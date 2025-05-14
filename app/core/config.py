from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, RedisDsn
from typing import List, Union
import os

# Define the base directory of the application
# This assumes config.py is in app/core/
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    PROJECT_NAME: str = "The Ashoka Buddhist Foundation"
    API_V1_STR: str = "/api/v1"
    WEB_APP_BASE_URL: str = "http://localhost:8000"

    # Security
    SECRET_KEY: (
        str  # Example: "your-very-strong-and-long-secret-key-here" - SET IN .ENV
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database (PostgreSQL)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "ashoka_user"  # Example user
    POSTGRES_PASSWORD: str = "ashoka_pass"  # Example password - SET IN .ENV
    POSTGRES_DB: str = "ashoka_db"  # Example DB name
    DATABASE_URL: Union[PostgresDsn, str] = ""
    DB_POOL_SIZE: int = 15
    DB_MAX_OVERFLOW: int = 30

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB_MAIN: int = 0  # For caching
    REDIS_DB_CELERY: int = 1  # For Celery broker/backend
    REDIS_PASSWORD: str | None = None  # SET IN .ENV IF USED
    REDIS_URL_MAIN: Union[RedisDsn, str] = ""
    REDIS_URL_CELERY: Union[RedisDsn, str] = ""

    # Celery
    CELERY_BROKER_URL: Union[RedisDsn, str] = ""  # Assembled from REDIS_URL_CELERY
    CELERY_RESULT_BACKEND_URL: Union[RedisDsn, str] = (
        ""  # Assembled from REDIS_URL_CELERY
    )

    # Static and Templates
    STATIC_DIR: str = os.path.join(APP_DIR, "static")
    TEMPLATES_DIR: str = os.path.join(APP_DIR, "web", "templates")

    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    SMTP_TLS: bool = True
    SMTP_PORT: int | None = 587
    SMTP_HOST: str | None = None  # e.g., "smtp.mailgun.org" - SET IN .ENV
    SMTP_USER: str | None = None  # SET IN .ENV
    SMTP_PASSWORD: str | None = None  # SET IN .ENV
    EMAILS_FROM_EMAIL: str | None = "noreply@ashokafoundation.org"
    EMAILS_FROM_NAME: str | None = PROJECT_NAME

    ENVIRONMENT: str = "development"  # development, staging, production

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    def __init__(self, **values):
        super().__init__(**values)
        if not self.DATABASE_URL:
            self.DATABASE_URL = str(
                PostgresDsn.build(
                    scheme="postgresql+asyncpg",
                    username=self.POSTGRES_USER,
                    password=self.POSTGRES_PASSWORD,
                    host=self.POSTGRES_SERVER,
                    path=f"/{self.POSTGRES_DB}",
                )
            )
        if not self.REDIS_URL_MAIN:
            self.REDIS_URL_MAIN = str(
                RedisDsn.build(
                    scheme="redis",
                    host=self.REDIS_HOST,
                    port=self.REDIS_PORT,
                    path=f"/{self.REDIS_DB_MAIN}",
                    password=self.REDIS_PASSWORD,
                )
            )
        if not self.REDIS_URL_CELERY:
            self.REDIS_URL_CELERY = str(
                RedisDsn.build(
                    scheme="redis",
                    host=self.REDIS_HOST,
                    port=self.REDIS_PORT,
                    path=f"/{self.REDIS_DB_CELERY}",
                    password=self.REDIS_PASSWORD,
                )
            )
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.REDIS_URL_CELERY
        if not self.CELERY_RESULT_BACKEND_URL:
            self.CELERY_RESULT_BACKEND_URL = self.REDIS_URL_CELERY


settings = Settings()
