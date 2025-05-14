from fastapi import APIRouter, Request, Depends, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession  # If needed for dashboard data
from app.core.security import get_current_active_user_web  # Ensures active user
from app.db.models.user_model import User  # For type hinting
from app.main import templates  # Import global templates instance
from app.core.config import settings
from app.db.schemas import user_schemas, token_schemas  # Added this import

router = APIRouter(prefix="/dashboard", tags=["Web Dashboard"])


@router.get("/", response_class=HTMLResponse, name="dashboard_page")
async def dashboard_get(
    request: Request, current_user: User = Depends(get_current_active_user_web)
):
    # This route will only be accessible if the user is logged in and active.
    # The get_current_active_user_web dependency handles the redirection/error if not.
    # However, it raises HTTPException. We need to catch this or handle redirection in middleware or main error handler.
    # For now, let's assume if we reach here, user is authenticated.
    # For a more robust solution, a middleware checking auth for /dashboard paths and redirecting is better.

    # If the dependency itself doesn't redirect but raises HTTPException,
    # a custom exception handler in main.py for 401 could redirect to login for HTML requests.
    if not current_user:  # Should not happen if dependency is correctly configured
        return RedirectResponse(
            url=request.url_for("login_page") + "?next=" + str(request.url),
            status_code=status.HTTP_302_FOUND,  # Corrected status code
        )

    return templates.TemplateResponse(
        "dashboard/dashboard.html",
        {"request": request, "title": "My Dashboard", "current_user": current_user},
    )
