# app/web/routers/auth_web.py
import re  # For password validation
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError  # Ensure ValidationError is imported

from app.core.config import settings
from app.db import database
from app.db.schemas import user_schemas, token_schemas  # This will now use your stricter schemas
from app.services.auth_service import auth_service_web
from app.core.security import (
    get_current_user_from_cookie_web,
    clear_auth_cookies,
    set_auth_cookies,
)
from app.db.models.user_model import User
from app.core.templating import templates

router = APIRouter(prefix="/auth", tags=["Web Authentication"])


# Helper function for password strength validation
# This function remains as is. Pydantic UserCreate schema will enforce its own
# password min_length (12) before this strength check is called.
# If settings.MIN_PASSWORD_LENGTH is different, this function will apply that
# in addition to other strength criteria.
def _validate_password_strength(password: str) -> list[str]:
    """
    Validates password strength based on criteria.
    Criteria can be configured via app.core.config.settings.
    Returns a list of error messages if validation fails, otherwise an empty list.
    """
    errors = []

    # This min_length is from settings, UserCreate schema has its own (e.g., 12)
    # Pydantic validation for UserCreate.password happens before this.
    # If UserCreate.password (min 12) passes, and settings.MIN_PASSWORD_LENGTH is 8, this check passes.
    # If settings.MIN_PASSWORD_LENGTH is 15, this check would add an error.
    min_length_setting = getattr(settings, "MIN_PASSWORD_LENGTH", 8)
    if len(password) < min_length_setting:
        errors.append(f"Password must be at least {min_length_setting} characters long (policy).")

    if getattr(settings, "REQUIRE_PASSWORD_UPPERCASE", True) and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter.")

    if getattr(settings, "REQUIRE_PASSWORD_LOWERCASE", True) and not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter.")

    if getattr(settings, "REQUIRE_PASSWORD_DIGIT", True) and not re.search(r"\d", password):
        errors.append("Password must contain at least one digit.")

    special_char_regex = r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?~`]"
    if getattr(settings, "REQUIRE_PASSWORD_SPECIAL_CHAR", True) and not re.search(
        special_char_regex, password
    ):
        errors.append("Password must contain at least one special character (e.g., !@#$%^&*).")

    return errors


@router.get("/login", response_class=HTMLResponse, name="login_page")
async def login_get(
    request: Request,
    current_user: User | None = Depends(get_current_user_from_cookie_web),
):
    if current_user:
        return RedirectResponse(
            url=request.url_for("dashboard_page"), status_code=status.HTTP_302_FOUND
        )
    template = templates.get_template("auth/login.html")
    content = await template.render_async({"request": request, "title": "Login", "form_data": {}})
    return HTMLResponse(content)


@router.post("/login", name="login_post")
async def login_post(
    request: Request,
    db: AsyncSession = Depends(database.get_async_db),
    username_or_email: str = Form(...),
    password: str = Form(...),
):
    form_repopulate_data = {"username_or_email": username_or_email}

    try:
        # Pydantic validation now uses the stricter UserLoginSchema
        # with its custom validator for username_or_email.
        form_data_model = user_schemas.UserLoginSchema(
            username_or_email=username_or_email, password=password
        )

        _user, access_token, refresh_token = await auth_service_web.login_web(
            db=db, form_data=form_data_model
        )

        request.session["flash_success"] = "Login successful!"
        next_url_param = request.query_params.get("next")
        redirect_url_str = next_url_param if next_url_param else request.url_for("dashboard_page")
        actual_response = RedirectResponse(url=redirect_url_str, status_code=status.HTTP_302_FOUND)
        set_auth_cookies(actual_response, access_token, refresh_token)
        return actual_response

    except ValidationError as e:
        # Pydantic errors from UserLoginSchema (e.g., "Invalid email format", "Invalid username format")
        # will be caught here. For login, we still provide a somewhat generic message.
        # We can extract the first error message for slightly more context if desired,
        # but avoid overly detailed field-specific errors for login security.
        first_error_msg = (
            e.errors()[0].get("msg", "Please check your input.")
            if e.errors()
            else "Please check your input."
        )
        error_detail = f"Login failed. {first_error_msg}"
        # Or, stick to a very generic one:
        # error_detail = "Invalid username/email or password. Please check your input and try again."

        template = templates.get_template("auth/login.html")
        context = {
            "request": request,
            "title": "Login",
            "form_data": form_repopulate_data,
            "error_message": error_detail,
        }
        content = await template.render_async(context)
        return HTMLResponse(content, status_code=status.HTTP_400_BAD_REQUEST)

    except HTTPException as e:
        template = templates.get_template("auth/login.html")
        context = {
            "request": request,
            "title": "Login",
            "form_data": form_repopulate_data,
            "error_message": e.detail,  # e.g., "Invalid credentials" from service layer
        }
        content = await template.render_async(context)
        response_status_code = (
            e.status_code if hasattr(e, "status_code") else status.HTTP_400_BAD_REQUEST
        )
        return HTMLResponse(content, status_code=response_status_code)


@router.get("/register", response_class=HTMLResponse, name="register_page")
async def register_get(
    request: Request,
    current_user: User | None = Depends(get_current_user_from_cookie_web),
):
    if current_user:
        return RedirectResponse(
            url=request.url_for("dashboard_page"), status_code=status.HTTP_302_FOUND
        )
    template = templates.get_template("auth/register.html")
    content = await template.render_async(
        {"request": request, "title": "Register", "form_data": {}}
    )
    return HTMLResponse(content)


@router.post("/register", name="register_post")
async def register_post(
    request: Request,
    db: AsyncSession = Depends(database.get_async_db),
    username: str = Form(...),
    email: str = Form(...),
    full_name: str | None = Form(None),  # Pydantic will handle None for optional field
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    form_repopulate_data = {
        "username": username,
        "email": email,
        "full_name": full_name if full_name else "",  # Keep repopulating as string for form
    }
    error_message: str | None = None
    field_errors: dict[str, str | list[str]] = {}
    caught_exception: Exception | None = None

    # 1. Password confirmation check (remains important)
    if password != confirm_password:
        field_errors["confirm_password"] = "Passwords do not match."

    # 2. Password strength policy check (e.g., uppercase, digit, special char)
    # This runs AFTER Pydantic's UserCreate schema validation (which includes min_length=12 for password)
    # if we proceed to the try block.
    # It's better to run this custom validation alongside other form-level checks *before* Pydantic.
    password_strength_issues = _validate_password_strength(password)
    if password_strength_issues:
        # If field_errors["password"] already exists (e.g. from Pydantic), append.
        # However, Pydantic errors are handled in the except block.
        # This assumes _validate_password_strength is a primary check.
        if "password" in field_errors and isinstance(field_errors["password"], list):
            field_errors["password"].extend(password_strength_issues)  # type: ignore
        else:
            field_errors["password"] = password_strength_issues

    # 3. Determine overall error message if any field errors exist from these initial custom validations
    if field_errors:
        # This block handles errors from password mismatch and _validate_password_strength
        # Pydantic errors are handled in the `except ValidationError` block later.
        # We need to combine these error sources if Pydantic validation also fails.
        # For now, if these initial checks fail, we return early.
        if "confirm_password" in field_errors and "password" in field_errors:
            error_message = "Registration failed. Passwords do not match and/or the password does not meet strength requirements. Please check below."
        elif "confirm_password" in field_errors:
            error_message = "Passwords do not match."
        elif "password" in field_errors:
            error_message = "Password does not meet all strength requirements. Please check below."

        if not error_message and field_errors:  # Fallback
            error_message = "Registration failed. Please correct the errors highlighted below."

        template = templates.get_template("auth/register.html")
        context = {
            "request": request,
            "title": "Register",
            "form_data": form_repopulate_data,
            "error_message": error_message,
            "errors": field_errors,  # field_errors from confirm_password and _validate_password_strength
        }
        content = await template.render_async(context)
        return HTMLResponse(content, status_code=status.HTTP_400_BAD_REQUEST)

    # 4. If initial custom validations passed, proceed to Pydantic schema validation and service layer
    try:
        # Pydantic UserCreate schema will now apply its strict rules (min/max length, regex, bleach, etc.)
        # This includes password min_length=12.
        user_in_schema = user_schemas.UserCreate(
            username=username,
            email=email,
            full_name=full_name if full_name else None,  # Pass None if empty for Pydantic optional
            password=password,
        )
        # If Pydantic validation passes, proceed to service layer
        await auth_service_web.register_web(db=db, user_in=user_in_schema)

        request.session["flash_success"] = "Registration successful! Please login."
        return RedirectResponse(
            url=request.url_for("login_page"), status_code=status.HTTP_303_SEE_OTHER
        )

    except ValidationError as e:
        caught_exception = e
        # Pydantic errors are now more specific due to stricter schemas.
        # The existing loop should populate field_errors correctly.
        pydantic_error_messages_list = []
        for err_dict in e.errors():
            loc = err_dict.get("loc", ("form",))
            field_name = str(loc[-1]) if loc and isinstance(loc, tuple) and loc else "form"
            msg = err_dict.get("msg", "Invalid input.")

            # Ensure field_errors from Pydantic are added/merged correctly
            # with any pre-existing errors (though the current flow returns early if pre-existing errors).
            # This part assumes field_errors might not be populated yet if initial checks passed.
            if field_name in field_errors:
                if isinstance(field_errors[field_name], list):
                    if msg not in field_errors[field_name]:  # type: ignore
                        field_errors[field_name].append(msg)  # type: ignore
                elif field_errors[field_name] != msg:  # If it was a string, make it a list
                    field_errors[field_name] = [str(field_errors[field_name]), msg]  # type: ignore
            elif (
                field_name == "password"
                and "password" in field_errors
                and isinstance(field_errors["password"], list)
            ):
                # If password field already has strength errors, append Pydantic's message
                if msg not in field_errors["password"]:  # type: ignore
                    field_errors["password"].append(msg)  # type: ignore
            else:
                field_errors[field_name] = msg

            pydantic_error_messages_list.append(f"{field_name.capitalize()}: {msg}")

        if pydantic_error_messages_list:
            error_message = "Validation error: " + "; ".join(pydantic_error_messages_list)
        else:
            error_message = "Invalid registration data. Please check your inputs."

        # If there were also password strength/match errors from before, refine the general message
        if "confirm_password" in field_errors or (
            "password" in field_errors
            and any("policy" in item or "strength" in item for item in field_errors["password"])
        ):  # type: ignore
            error_message = "Registration failed. Please correct all highlighted errors below."

    except HTTPException as e:
        caught_exception = e
        error_message = e.detail
        detail_lower = e.detail.lower()
        identity_keywords = ["exists", "taken", "registered", "already in use", "duplicate"]
        if "username" in detail_lower and any(k in detail_lower for k in identity_keywords):
            field_errors["username"] = e.detail
        elif "email" in detail_lower and any(k in detail_lower for k in identity_keywords):
            field_errors["email"] = e.detail

    # 5. If any error occurred (initial validation, Pydantic, or service HTTPException), re-render
    if (
        caught_exception or error_message
    ):  # error_message might be set by initial checks even if no exception
        template = templates.get_template("auth/register.html")
        context = {
            "request": request,
            "title": "Register",
            "form_data": form_repopulate_data,
            "error_message": error_message if error_message else "An error occurred.",
            "errors": field_errors,
        }
        content = await template.render_async(context)

        response_status_code = status.HTTP_400_BAD_REQUEST
        if isinstance(caught_exception, HTTPException):
            response_status_code = caught_exception.status_code
        # For ValidationError (Pydantic), 400 is fine for HTML forms.

        return HTMLResponse(content, status_code=response_status_code)

    # Fallback
    request.session["flash_error"] = "An unexpected error occurred during registration."
    return RedirectResponse(
        url=request.url_for("register_page"), status_code=status.HTTP_302_FOUND
    )


@router.get("/logout", name="logout")
async def logout(request: Request):
    actual_response = RedirectResponse(
        url=request.url_for("home_page"), status_code=status.HTTP_302_FOUND
    )
    clear_auth_cookies(actual_response)
    request.session["flash_info"] = "You have been logged out."
    return actual_response


@router.post("/refresh-token", name="refresh_token_web")
async def handle_refresh_token_web(
    request: Request,
    db: AsyncSession = Depends(database.get_async_db),
):
    try:
        new_access_token, new_refresh_token = await auth_service_web.refresh_access_token_web(
            request=request,
            db=db,
        )
        json_content = token_schemas.Token(
            access_token=new_access_token, refresh_token=new_refresh_token
        ).model_dump()
        actual_response = JSONResponse(content=json_content)
        set_auth_cookies(actual_response, new_access_token, new_refresh_token)
        return actual_response
    except HTTPException as e:
        error_response_content = {"detail": e.detail}
        actual_error_response = JSONResponse(
            content=error_response_content, status_code=e.status_code
        )
        clear_auth_cookies(actual_error_response)
        return actual_error_response
