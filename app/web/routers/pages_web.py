from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from app.core.security import get_current_user_from_cookie_web  # Optional user
from app.db.models.user_model import User  # For type hinting
from typing import Optional
from app.main import templates

router = APIRouter(tags=["Web Pages"])


@router.get("/", response_class=HTMLResponse, name="home_page")
async def home_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_from_cookie_web),
):
    return templates.TemplateResponse(
        "pages/index.html",
        {"request": request, "current_user": current_user, "title": "Home"},
    )


@router.get("/about", response_class=HTMLResponse, name="about_page")
async def about_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_from_cookie_web),
):
    return templates.TemplateResponse(
        "pages/about.html",
        {"request": request, "current_user": current_user, "title": "About Us"},
    )


# Add other static pages like /contact, /teachings (listings) etc.
