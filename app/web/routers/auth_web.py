# app/web/routers/auth_web.py
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import database
from app.db.schemas import user_schemas, token_schemas
from app.services.auth_service import auth_service_web
from app.core.security import (
    get_current_user_from_cookie_web,
    clear_auth_cookies,
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
    response: Response,
    db: AsyncSession = Depends(database.get_async_db),
    username_or_email: str = Form(...),
    password: str = Form(...),
):
    form_data_model = user_schemas.UserLoginSchema(
        username_or_email=username_or_email, password=password
    )
    try:
        await auth_service_web.login_web(db=db, response=response, form_data=form_data_model)
        request.session["flash_success"] = "Login successful!"
        # Check for 'next' URL parameter for redirection after login
        next_url = request.query_params.get("next")
        if next_url:
            return RedirectResponse(url=next_url, status_code=status.HTTP_302_FOUND)
        return RedirectResponse(
            url=request.url_for("dashboard_page"), status_code=status.HTTP_302_FOUND
        )
    except HTTPException as e:
        # Re-render the login form with an error message and repopulate username
        request.session["flash_error"] = e.detail  # For general flash message display

        template = templates.get_template("auth/login.html")
        form_repopulate_data = {"username_or_email": username_or_email}

        context = {
            "request": request,
            "title": "Login",
            "form_data": form_repopulate_data,
            "error_message": e.detail,  # Specific error message for the form
        }
        content = await template.render_async(context)
        # Use the status code from the exception (e.g., 400, 401)
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
async def logout(request: Request, response: Response):
    await auth_service_web.logout_web(response=response)
    request.session["flash_info"] = "You have been logged out."
    return RedirectResponse(url=request.url_for("home_page"), status_code=status.HTTP_302_FOUND)


@router.post("/refresh-token", name="refresh_token_web", response_model=token_schemas.Token)
async def handle_refresh_token_web(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(database.get_async_db),
):
    """Endpoint to refresh access token using refresh token from cookie."""
    try:
        return await auth_service_web.refresh_access_token_web(
            request=request, response=response, db=db
        )
    except HTTPException as e:
        # If refresh fails, clear auth cookies.
        # The client (JS) should handle the HTTP error response.
        clear_auth_cookies(response)
        raise e
