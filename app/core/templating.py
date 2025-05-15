from fastapi.templating import Jinja2Templates
from app.core.config import settings
from jinja2_time import TimeExtension  # <--- Import the extension
import datetime


def format_date(value, format="%Y-%m-%d"):
    """Jinja2 filter to format a date."""
    if value == "now":
        dt = datetime.datetime.now()
    elif isinstance(value, (datetime.datetime, datetime.date)):
        dt = value
    else:
        # Attempt to parse other types if necessary, or handle errors
        try:
            # Example: try parsing as a string
            dt = datetime.datetime.strptime(str(value), "%Y-%m-%d")  # Adjust format as needed
        except (ValueError, TypeError):
            # If parsing fails, maybe return the original value or an error message
            return str(value)  # Or raise an error

    return dt.strftime(format)


# Initialize Jinja2Templates
# The 'directory' should point to your 'templates' folder.
# settings.TEMPLATES_DIR should be defined in your app.core.config.py
templates = Jinja2Templates(
    directory=str(settings.TEMPLATES_DIR),
    enable_async=True,
    extensions=["jinja2_time.TimeExtension"],  # <--- Add the TimeExtension here
)

templates.env.filters["date"] = format_date

# Make the 'settings' object available globally in all templates
templates.env.globals["settings"] = settings

# You can also add other custom global functions or variables here if needed.
# For example:
# import datetime
# def get_current_year():
#     return datetime.datetime.now(datetime.timezone.utc).year
# templates.env.globals["current_year"] = get_current_year
# Then in template: {{ current_year }} (if you didn't want to use {% now %})
