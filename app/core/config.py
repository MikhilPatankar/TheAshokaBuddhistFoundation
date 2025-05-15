# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, RedisDsn
from typing import List, Union
import os
# import ssl as py_ssl # Not strictly needed here if we use string values for cert_reqs

# Define the base directory of the application
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    PROJECT_NAME: str = "The Ashoka Buddhist Foundation"
    API_V1_STR: str = "/api/v1"
    WEB_APP_BASE_URL: str = "http://localhost:8000"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database (PostgreSQL)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "ashoka_user"
    POSTGRES_PASSWORD: str = "ashoka_pass"
    POSTGRES_DB: str = "ashoka_db"
    DATABASE_URL: Union[PostgresDsn, str] = ""
    DB_POOL_SIZE: int = 15
    DB_MAX_OVERFLOW: int = 30

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_USER: str | None = None
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0
    REDIS_DB_CELERY: int = 1
    REDIS_SSL: bool = False  # Set to True in .env for SSL (e.g., Aiven)
    REDIS_SSL_CERT_REQS: str = (
        "CERT_REQUIRED"  # Default: "CERT_REQUIRED", "CERT_OPTIONAL", or "CERT_NONE"
    )
    REDIS_URL: Union[RedisDsn, str] = ""
    REDIS_URL_CELERY: Union[RedisDsn, str] = ""

    # Celery
    CELERY_BROKER_URL: Union[RedisDsn, str] = ""
    CELERY_RESULT_BACKEND_URL: Union[RedisDsn, str] = ""

    # Static and Templates
    STATIC_DIR: str = os.path.join(APP_DIR, "static")
    TEMPLATES_DIR: str = os.path.join(APP_DIR, "web", "templates")

    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    SMTP_TLS: bool = True
    SMTP_PORT: int | None = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: str | None = "noreply@ashokafoundation.org"
    EMAILS_FROM_NAME: str | None = PROJECT_NAME

    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def __init__(self, **values):
        super().__init__(**values)

        # --- PostgreSQL URL ---
        if not self.DATABASE_URL:  # Only construct if not explicitly set in .env
            # Check if POSTGRES_SERVER already includes port
            pg_host_port = self.POSTGRES_SERVER.split(":")
            pg_host = pg_host_port[0]
            pg_port = (
                pg_host_port[1] if len(pg_host_port) > 1 else None
            )  # Pydantic handles default port

            self.DATABASE_URL = str(
                PostgresDsn.build(
                    scheme="postgresql+asyncpg",
                    username=self.POSTGRES_USER,
                    password=self.POSTGRES_PASSWORD,
                    host=pg_host,
                    port=int(pg_port) if pg_port else None,
                    path=f"/{self.POSTGRES_DB}",
                )
            )
            # For Aiven PG with SSL: append ?ssl=require if not already in a fully qualified DATABASE_URL
            # However, your .env already has DATABASE_URL with ?ssl=require, so this block might not run for PG.
            # If DATABASE_URL is NOT set in .env, and you need SSL for PG:
            # if "aivencloud.com" in self.POSTGRES_SERVER and "?ssl=" not in self.DATABASE_URL:
            #    self.DATABASE_URL += "?ssl=require"

        # --- Redis URLs ---
        effective_redis_scheme = "rediss" if self.REDIS_SSL else "redis"
        valid_cert_reqs_options = ["CERT_REQUIRED", "CERT_OPTIONAL", "CERT_NONE"]
        current_cert_reqs = self.REDIS_SSL_CERT_REQS.upper()

        if self.REDIS_SSL and current_cert_reqs not in valid_cert_reqs_options:
            raise ValueError(
                f"REDIS_SSL_CERT_REQS (current: {self.REDIS_SSL_CERT_REQS}) "
                f"must be one of {valid_cert_reqs_options}"
            )

        # For general Redis (caching)
        if not self.REDIS_URL:  # Only construct if not explicitly set in .env
            base_url_main_obj = RedisDsn.build(
                scheme=effective_redis_scheme,
                username=self.REDIS_USER,
                password=self.REDIS_PASSWORD,
                host=self.REDIS_HOST,
                port=self.REDIS_PORT,
                path=f"/{self.REDIS_DB}",
            )
            if self.REDIS_SSL:
                self.REDIS_URL = f"{str(base_url_main_obj)}?ssl_cert_reqs={current_cert_reqs}"
            else:
                self.REDIS_URL = str(base_url_main_obj)

        # For Celery broker/backend
        if not self.REDIS_URL_CELERY:  # Only construct if not explicitly set in .env
            base_url_celery_obj = RedisDsn.build(
                scheme=effective_redis_scheme,
                username=self.REDIS_USER,
                password=self.REDIS_PASSWORD,
                host=self.REDIS_HOST,
                port=self.REDIS_PORT,
                path=f"{self.REDIS_DB_CELERY}",
            )
            if self.REDIS_SSL:
                self.REDIS_URL_CELERY = (
                    f"{str(base_url_celery_obj)}?ssl_cert_reqs={current_cert_reqs}"
                )
            else:
                self.REDIS_URL_CELERY = str(base_url_celery_obj)

        # --- Celery URLs ---
        # These will use the REDIS_URL_CELERY constructed above if not set in .env
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.REDIS_URL_CELERY
        if not self.CELERY_RESULT_BACKEND_URL:
            self.CELERY_RESULT_BACKEND_URL = self.REDIS_URL_CELERY


settings = Settings()
