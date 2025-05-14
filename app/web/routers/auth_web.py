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
)  # Renamed dependency
from app.db.models.user_model import User  # For type hinting
from app.main import templates  # Import global templates instance

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
    return templates.TemplateResponse(
        "auth/login.html", {"request": request, "title": "Login"}
    )


@router.post("/login", name="login_post")
async def login_post(
    request: Request,
    response: Response,  # FastAPI will inject this
    db: AsyncSession = Depends(database.get_async_db),
    username_or_email: str = Form(...),
    password: str = Form(...),
):
    form_data = user_schemas.UserLoginSchema(
        username_or_email=username_or_email, password=password
    )
    try:
        await auth_service_web.login_web(db=db, response=response, form_data=form_data)
        # Add flash message for success
        request.session["flash_success"] = "Login successful!"
        return RedirectResponse(
            url=request.url_for("dashboard_page"), status_code=status.HTTP_302_FOUND
        )
    except HTTPException as e:
        # Add flash message for error
        request.session["flash_error"] = e.detail
        return RedirectResponse(
            url=request.url_for("login_page"), status_code=status.HTTP_303_SEE_OTHER
        )


@router.get("/register", response_class=HTMLResponse, name="register_page")
async def register_get(
    request: Request,
    current_user: User | None = Depends(get_current_user_from_cookie_web),
):
    if current_user:
        return RedirectResponse(
            url=request.url_for("dashboard_page"), status_code=status.HTTP_302_FOUND
        )
    return templates.TemplateResponse(
        "auth/register.html", {"request": request, "title": "Register", "form_data": {}}
    )


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
    form_data_dict = {
        "username": username,
        "email": email,
        "full_name": full_name,
        "password": password,
    }
    if password != confirm_password:
        request.session["flash_error"] = "Passwords do not match."
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "title": "Register",
                "form_data": form_data_dict,
                "errors": {"confirm_password": "Passwords do not match."},
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

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
        request.session["flash_error"] = e.detail
        # To pass errors back to the template specific to fields, you'd need more complex error handling
        # or rely on client-side validation + generic server errors for now.
        # For simplicity, we'll show a general error.
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "title": "Register", "form_data": form_data_dict},
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@router.get("/logout", name="logout")
async def logout(request: Request, response: Response):  # Ensure response is injected
    await auth_service_web.logout_web(response=response)
    request.session["flash_info"] = "You have been logged out."
    return RedirectResponse(
        url=request.url_for("home_page"), status_code=status.HTTP_302_FOUND
    )


@router.post(
    "/refresh-token", name="refresh_token_web", response_model=token_schemas.Token
)
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
        # If refresh fails, redirect to login
        clear_auth_cookies(response)  # Ensure cookies are cleared
        # This endpoint is typically called by JS, but for a full page context, redirect
        # For JS clients, they'd handle the JSON error.
        # If called from a context where redirect is okay:
        # request.session["flash_error"] = "Your session has expired. Please login again."
        # return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_303_SEE_OTHER)
        raise e  # Let the client handle the JSON error if it's an XHR call
