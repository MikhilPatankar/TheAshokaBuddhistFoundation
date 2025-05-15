from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles

# from fastapi.templating import Jinja2Templates # Already handled by app.core.templating
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from jinja2.exceptions import TemplateNotFound  # Import this for specific exception handling

from app.core.config import settings
from app.core.lifespan import lifespan
from app.core.templating import templates  # Your Jinja2Templates instance
from app.web.routers import pages_web, auth_web, dashboard_web
from app.utils.logging_config import setup_logging

import logging  # For logging within the handler

setup_logging()  # Call if defined
logger = logging.getLogger(__name__)  # Initialize a logger for this module

app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url=(f"{settings.API_V1_STR}/docs" if settings.ENVIRONMENT == "development" else None),
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

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    https_only=settings.ENVIRONMENT != "development",
)

# --- Static Files & Templates ---
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

# --- Routers ---
app.include_router(pages_web.router)
app.include_router(auth_web.router)
app.include_router(dashboard_web.router)


# --- Custom Exception Handlers ---
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    accept_header = request.headers.get("accept", "")

    # Check if the client prefers HTML response
    if "text/html" in accept_header:
        if exc.status_code == 401:  # Unauthorized
            login_url = request.url_for(
                "login_page"
            )  # Assuming 'login_page' is the name of your login route
            redirect_url_obj = login_url.include_query_params(next=str(request.url))

            if hasattr(request, "session"):  # Check if session middleware is active
                request.session["flash_warning"] = "Please login to access this page."

            return RedirectResponse(url=str(redirect_url_obj), status_code=status.HTTP_302_FOUND)

        # Handle other HTML errors (e.g., 404, 500)
        error_template_name = f"errors/{exc.status_code}.html"
        generic_error_template_name = "errors/generic_error.html"
        chosen_template_name: str

        try:
            templates.get_template(error_template_name)  # Check if specific template exists
            chosen_template_name = error_template_name
        except TemplateNotFound:
            logger.debug(
                f"Specific error template {error_template_name} not found. Falling back to generic."
            )
            chosen_template_name = generic_error_template_name
        except Exception as e_check:
            # Log other unexpected errors during template existence check
            logger.error(
                f"Unexpected error when checking for template {error_template_name}: {e_check}",
                exc_info=True,
            )
            chosen_template_name = generic_error_template_name  # Fallback to generic

        context = {
            "request": request,
            "title": f"Error {exc.status_code}",
            "status_code": exc.status_code,  # Explicitly pass status_code
            "detail": exc.detail,
            "current_user": (
                request.state.current_user if hasattr(request.state, "current_user") else None
            ),
        }

        try:
            # --- MODIFIED SECTION: Use get_template and render_async ---
            template_obj = templates.get_template(chosen_template_name)
            content = await template_obj.render_async(context)
            return HTMLResponse(content=content, status_code=exc.status_code)
            # --- END MODIFIED SECTION ---

        except TemplateNotFound:
            # This means chosen_template_name (likely generic_error_template_name) is missing.
            logger.critical(
                f"Core error template '{chosen_template_name}' not found. "
                f"This usually means '{generic_error_template_name}' is missing or inaccessible. "
                f"Falling back to basic HTML error response."
            )
            # Provide a very basic HTML response as an ultimate fallback
            fallback_html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Error {exc.status_code}</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 0; padding: 20px; color: #333; text-align: center; }}
                    .container {{ max-width: 600px; margin: 50px auto; padding: 20px; background-color: #f9f9f9; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                    h1 {{ color: #d9534f; font-size: 2em; margin-bottom: 0.5em; }}
                    p {{ font-size: 1.1em; line-height: 1.6; }}
                    .detail {{ color: #555; margin-bottom: 1.5em;}}
                    .info {{ font-size: 0.9em; color: #777; margin-top: 2em; }}
                    a {{ color: #007bff; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Error {exc.status_code}</h1>
                    <p class="detail">{exc.detail if exc.detail else "An unexpected error occurred."}</p>
                    <p><a href="{request.app.url_path_for("home_page" if "home_page" in request.app.router.routes_by_name else "/")}">Go to Homepage</a></p>
                    <p class="info"><i>The standard error page template could not be loaded.</i></p>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=fallback_html_content, status_code=exc.status_code)
        except Exception as e_render:
            # Catch any other rendering errors.
            logger.error(
                f"Failed to render HTML error page with template '{chosen_template_name}' for status {exc.status_code}: {e_render}",
                exc_info=True,
            )
            # Fallback to FastAPI's default non-HTML error handler if template rendering fails for other reasons
            from fastapi.exception_handlers import (
                http_exception_handler as fastapi_http_exception_handler,
            )

            return await fastapi_http_exception_handler(request, exc)

    # If client does not prefer HTML, or it's not a handled HTML error code,
    # use the default FastAPI/Starlette exception handler for JSON responses etc.
    from fastapi.exception_handlers import (
        http_exception_handler as fastapi_http_exception_handler,
    )

    return await fastapi_http_exception_handler(request, exc)


# ... (rest of your main.py, including the add_user_to_request_state middleware if you use it, and uvicorn.run) ...


# Example of add_user_to_request_state (keep your existing logic or refine as needed)
@app.middleware("http")
async def add_user_to_request_state(request: Request, call_next):
    # Your existing logic for setting request.state.current_user
    # This middleware is just an example placeholder.
    # Ensure your actual middleware correctly handles DB sessions if needed.
    response = await call_next(request)
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=80, reload=True)
