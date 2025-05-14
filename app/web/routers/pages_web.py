from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse  # Ensure HTMLResponse is imported
from app.core.security import get_current_user_from_cookie_web  # Optional user
from app.db.models.user_model import User  # For type hinting
from typing import Optional
from app.core.templating import templates

router = APIRouter(tags=["Web Pages"])


@router.get("/", response_class=HTMLResponse, name="home_page")
async def home_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_from_cookie_web),
):
    # Get the template object
    template = templates.get_template("pages/index.html")
    # Render the template asynchronously
    content = await template.render_async(
        {"request": request, "current_user": current_user, "title": "Home"}
    )
    # Return an HTMLResponse with the rendered content
    return HTMLResponse(content)


@router.get("/about", response_class=HTMLResponse, name="about_page")
async def about_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_from_cookie_web),
):
    # Get the template object
    template = templates.get_template("pages/about.html")
    # Render the template asynchronously
    content = await template.render_async(
        {"request": request, "current_user": current_user, "title": "About Us"}
    )
    # Return an HTMLResponse with the rendered content
    return HTMLResponse(content)


# Add other static pages like /contact, /teachings (listings) etc.
# Remember to apply the same pattern (get_template, render_async, HTMLResponse)
# to any other async route using templates.
