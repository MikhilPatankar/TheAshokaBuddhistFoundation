from fastapi.templating import Jinja2Templates
from app.core.config import settings
from jinja2_time import TimeExtension  # <--- Import the extension

# Initialize Jinja2Templates
# The 'directory' should point to your 'templates' folder.
# settings.TEMPLATES_DIR should be defined in your app.core.config.py
templates = Jinja2Templates(
    directory=str(settings.TEMPLATES_DIR),
    enable_async=True,
    extensions=[TimeExtension],  # <--- Add the TimeExtension here
)

# Make the 'settings' object available globally in all templates
templates.env.globals["settings"] = settings

# You can also add other custom global functions or variables here if needed.
# For example:
# import datetime
# def get_current_year():
#     return datetime.datetime.now(datetime.timezone.utc).year
# templates.env.globals["current_year"] = get_current_year
# Then in template: {{ current_year }} (if you didn't want to use {% now %})
