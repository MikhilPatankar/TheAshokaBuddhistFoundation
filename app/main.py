from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

# from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware  # Import this
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.lifespan import lifespan
from app.core.templating import templates

# from app.api.v1 import api_router_v1 # If you have API routes
from app.web.routers import pages_web, auth_web, dashboard_web  # Import web routers
from app.utils.logging_config import setup_logging  # If you have this

setup_logging()  # Call if defined

app = FastAPI(
    title=settings.PROJECT_NAME,
    # openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.ENVIRONMENT == "development" else None,
    docs_url=(
        f"{settings.API_V1_STR}/docs" if settings.ENVIRONMENT == "development" else None
    ),
    # redoc_url=f"{settings.API_V1_STR}/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan,
)

# --- Middleware ---
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add SessionMiddleware for flash messages
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,  # Ensure this is a strong secret
    https_only=settings.ENVIRONMENT != "development",  # True in production
)

# --- Static Files & Templates ---
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")
# templates = Jinja2Templates(directory=settings.TEMPLATES_DIR, enable_async=True)

# --- Routers ---
# app.include_router(api_router_v1, prefix=settings.API_V1_STR) # If you have API routes
app.include_router(pages_web.router)  # Root pages
app.include_router(auth_web.router)  # Handles /auth prefix
app.include_router(dashboard_web.router)  # Handles /dashboard prefix


# --- Custom Exception Handlers ---
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        if exc.status_code == 401:  # Unauthorized
            request.session["flash_warning"] = "Please login to access this page."
            return RedirectResponse(
                url=request.url_for("login_page") + f"?next={request.url}",
                status_code=307,
            )

        template_name = f"errors/{exc.status_code}.html"
        # Fallback for other HTML errors (e.g., errors/500.html or a generic error.html)
        if exc.status_code == 404:
            return templates.TemplateResponse(
                template_name,
                {
                    "request": request,
                    "title": "Page Not Found",
                    "current_user": (
                        request.state.current_user
                        if hasattr(request.state, "current_user")
                        else None
                    ),
                },
                status_code=404,
            )
        return templates.TemplateResponse(
            "errors/500.html",
            {
                "request": request,
                "title": "Server Error",
                "detail": exc.detail,
                "current_user": (
                    request.state.current_user
                    if hasattr(request.state, "current_user")
                    else None
                ),
            },
            status_code=exc.status_code,
        )

    from fastapi.exception_handlers import (
        http_exception_handler as fastapi_http_exception_handler,
    )

    return await fastapi_http_exception_handler(request, exc)


# Example of adding current_user to request state via middleware (optional, but helpful for templates)
@app.middleware("http")
async def add_user_to_request_state(request: Request, call_next):
    from app.core.security import get_current_user_from_cookie_web
    from app.db.database import get_async_db

    # This is a simplified way; a proper dependency manager within middleware is complex.
    # For simplicity, we're re-fetching. Consider alternatives for performance.
    # This also doesn't handle DB session closure properly for this specific fetch.
    # A better way for global template context is to pass it from each route or use Jinja2 globals.
    # For this example, to make templates work without passing current_user everywhere, we'll do this:
    # However, this is NOT ideal for performance or DB session management.
    # The Depends() system in routes is the correct way.

    # For templates to access `current_user` globally *without passing from every route*,
    # Jinja2 globals are better. This middleware approach is less clean for DB access.
    # We will rely on passing `current_user` explicitly from routes via `Depends`.
    # So, this middleware part for `current_user` is illustrative but NOT recommended for this pattern.
    # request.state.current_user = await get_current_user_from_cookie_web(request, await anext(get_async_db())) # This line has issues with DB session.

    response = await call_next(request)
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
