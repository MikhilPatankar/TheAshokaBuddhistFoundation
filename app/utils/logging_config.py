# /home/mikhil_g_patankar/TheAshokaBuddhistFoundation/app/utils/logging_config.py
import logging
import sys

# from app.core.config import settings # Uncomment if you use settings.LOG_LEVEL


def setup_logging():
    """
    Basic logging configuration for the application.
    """
    # log_level_str = settings.LOG_LEVEL.upper() if hasattr(settings, "LOG_LEVEL") else "INFO"
    # log_level = getattr(logging, log_level_str, logging.INFO)
    log_level = logging.INFO  # Default to INFO, or use settings

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],  # Log to standard output
    )

    # Example: Set different levels for specific loggers if needed
    # logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    # logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("Logging configured.")


# If you want to configure logging as soon as this module is imported,
# you could call setup_logging() here. However, it's generally better
# to call it explicitly from main.py or your app's entry point.
