# app/web/routers/auth_web.py
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import database
from app.db.schemas import user_schemas, token_schemas
from app.services.auth_service import auth_service_web
from app.core.security import (
    get_current_user_from_cookie_web,
    clear_auth_cookies,
    set_auth_cookies,
)
from app.db.models.user_model import User
from app.core.templating import templates

router = APIRouter(prefix="/auth", tags=["Web Authentication"])


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
    # Pass empty form_data for initial render if template expects it
    content = await template.render_async({"request": request, "title": "Login", "form_data": {}})
    return HTMLResponse(content)


@router.post("/login", name="login_post")
async def login_post(
    request: Request,
    # response: Response, # REMOVE this injected parameter
    db: AsyncSession = Depends(database.get_async_db),
    username_or_email: str = Form(...),
    password: str = Form(...),
):
    form_data_model = user_schemas.UserLoginSchema(
        username_or_email=username_or_email, password=password
    )
    try:
        # login_web now returns user, access_token, refresh_token
        _user, access_token, refresh_token = await auth_service_web.login_web(
            db=db, form_data=form_data_model
        )

        request.session["flash_success"] = "Login successful!"

        next_url_param = request.query_params.get("next")
        redirect_url_str = next_url_param if next_url_param else request.url_for("dashboard_page")

        # Create the actual RedirectResponse
        actual_response = RedirectResponse(url=redirect_url_str, status_code=status.HTTP_302_FOUND)

        # Set cookies on THIS actual_response object
        set_auth_cookies(actual_response, access_token, refresh_token)

        return actual_response  # Return the response with cookies set

    except HTTPException as e:
        request.session["flash_error"] = e.detail
        template = templates.get_template("auth/login.html")
        form_repopulate_data = {"username_or_email": username_or_email}
        context = {
            "request": request,
            "title": "Login",
            "form_data": form_repopulate_data,
            "error_message": e.detail,
        }
        content = await template.render_async(context)
        response_status_code = (
            e.status_code if hasattr(e, "status_code") else status.HTTP_400_BAD_REQUEST
        )
        # Create HTMLResponse for error case
        error_response = HTMLResponse(content, status_code=response_status_code)
        # Cookies are not set on error, which is fine.
        return error_response


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
    full_name: str | None = Form(None),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    form_repopulate_data = {
        "username": username,
        "email": email,
        "full_name": full_name,
        # Do not repopulate password fields for security
    }

    if password != confirm_password:
        request.session["flash_error"] = "Passwords do not match."  # General flash
        template = templates.get_template("auth/register.html")
        context = {
            "request": request,
            "title": "Register",
            "form_data": form_repopulate_data,
            "errors": {"confirm_password": "Passwords do not match."},  # Specific field error
        }
        content = await template.render_async(context)
        return HTMLResponse(content, status_code=status.HTTP_400_BAD_REQUEST)

    user_in = user_schemas.UserCreate(
        username=username, email=email, full_name=full_name, password=password
    )
    try:
        await auth_service_web.register_web(db=db, user_in=user_in)
        request.session["flash_success"] = "Registration successful! Please login."
        return RedirectResponse(
            url=request.url_for("login_page"), status_code=status.HTTP_303_SEE_OTHER
        )
    except HTTPException as e:
        request.session["flash_error"] = e.detail  # General flash
        template = templates.get_template("auth/register.html")
        context = {
            "request": request,
            "title": "Register",
            "form_data": form_repopulate_data,
            "error_message": e.detail,  # Specific error message for the form
        }
        content = await template.render_async(context)
        response_status_code = (
            e.status_code if hasattr(e, "status_code") else status.HTTP_400_BAD_REQUEST
        )
        return HTMLResponse(content, status_code=response_status_code)


@router.get("/logout", name="logout")
async def logout(request: Request):
    actual_response = RedirectResponse(
        url=request.url_for("home_page"), status_code=status.HTTP_302_FOUND
    )
    clear_auth_cookies(actual_response)
    request.session["flash_info"] = "You have been logged out."
    return actual_response


@router.post("/refresh-token", name="refresh_token_web")  # Removed response_model for now
async def handle_refresh_token_web(
    request: Request,
    # response: Response, # REMOVE
    db: AsyncSession = Depends(database.get_async_db),
):
    try:
        new_access_token, new_refresh_token = await auth_service_web.refresh_access_token_web(
            request=request,
            db=db,  # Pass request, db
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
        clear_auth_cookies(actual_error_response)  # Clear cookies on error
        return actual_error_response
