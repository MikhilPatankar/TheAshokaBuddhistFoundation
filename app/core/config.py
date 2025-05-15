# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, RedisDsn
from typing import List, Union, Literal
import os

# Define the base directory of the application
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    PROJECT_NAME: str = "The Ashoka Buddhist Foundation"
    API_V1_STR: str = "/api/v1"
    WEB_APP_BASE_URL: str = "http://localhost:8000"

    # Info of foundation
    DESCRIPTION: str = ""  # General description, can be used as a fallback for meta description
    VERSION: str = "0.1.0"
    CONTACT_NAME: str = "The Ashoka Buddhist Foundation"
    CONTACT_EMAIL: str = ""
    CONTACT_NUMBER: str = "+91 90226 02287"
    CONTACT_ADDRESS: str = "VMV Rd, Ujjwal Colony"
    CONTACT_ADDRESS_2: str = "Navsaari"
    CONTACT_CITY: str = "Amravati"
    CONTACT_STATE: str = "Maharashtra"
    CONTACT_COUNTRY: str = "India"
    CONTACT_ZIP: str = ""
    CONTACT_WEBSITE: str = "https://theashokabuddhistfoundation.com"

    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "DEBUG"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database (PostgreSQL)
    POSTGRES_SERVER: str = ""
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
    DATABASE_URL: Union[PostgresDsn, str] = ""
    DB_POOL_SIZE: int = 15
    DB_MAX_OVERFLOW: int = 30

    # Redis
    REDIS_HOST: str = ""
    REDIS_PORT: int = 6379
    REDIS_USER: str | None = None
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0
    REDIS_DB_CELERY: int = 1
    REDIS_SSL: bool = False
    REDIS_SSL_CERT_REQS: str = "CERT_REQUIRED"
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
    EMAILS_FROM_NAME: str | None = None

    ENVIRONMENT: str = "development"

    # --- SEO Settings ---
    SITE_NAME: str = ""  # Public facing name of the site.
    DEFAULT_META_DESCRIPTION: str = ""  # Default meta description for pages.
    DEFAULT_META_KEYWORDS: str = "buddhism, mindfulness, meditation, wisdom, compassion, ashoka, foundation, spiritual, peace"
    CANONICAL_URL_BASE: str = ""  # Base for canonical URLs, e.g., https://yourdomain.com

    # Open Graph (Facebook, LinkedIn, etc.) & Twitter Card Defaults
    DEFAULT_OG_IMAGE_URL: str | None = (
        None  # Absolute URL to a default OG image (e.g., 1200x630px)
    )
    DEFAULT_OG_TYPE: str = "website"  # Common types: website, article, product
    TWITTER_SITE_HANDLE: str | None = None  # Site's Twitter @username (e.g., "@YourFoundation")
    TWITTER_CARD_TYPE: str = (
        "summary_large_image"  # "summary", "summary_large_image", "app", "player"
    )
    TWITTER_CREATOR_HANDLE: str | None = (
        None  # Twitter @username of the content creator/author (optional)
    )
    FACEBOOK_APP_ID: str | None = None  # For Facebook Insights and sharing features (optional)

    # Analytics & Verification
    GOOGLE_ANALYTICS_ID: str | None = None  # GA4: "G-XXXXXXXXXX", UA: "UA-XXXXX-Y"
    GOOGLE_SITE_VERIFICATION_ID: str | None = None  # For Google Search Console
    BING_SITE_VERIFICATION_ID: str | None = None  # For Bing Webmaster Tools
    # YANDEX_VERIFICATION_ID: str | None = None # If targeting Russian-speaking audiences
    # PINTEREST_VERIFICATION_ID: str | None = None # If relevant

    # Schema.org / Structured Data Defaults
    ORGANIZATION_SCHEMA_TYPE: str = "NGO"  # e.g., "Organization", "NGO", "EducationalOrganization"
    ORGANIZATION_LEGAL_NAME: str = ""  # Official legal name of the organization.
    ORGANIZATION_LOGO_URL: str | None = None  # Absolute URL to organization's logo (for Schema)
    ORGANIZATION_SAME_AS_URLS: List[
        str
    ] = []  # List of URLs to social media profiles or other official presences

    # Other SEO related
    SITE_LANG: str = "en-US"  # Default language-country code (e.g., "en-GB", "hi-IN")
    THEME_COLOR: str | None = None  # Browser theme color (e.g., "#003366")
    # FAVICON_URL: str | None = "/static/img/favicon.ico" # Path to favicon (can be relative)
    # APPLE_TOUCH_ICON_URL: str | None = "/static/img/apple-touch-icon.png" # Path to apple touch icon

    # Social Media Profile Links (useful for footer, schema, etc.)
    SOCIAL_PROFILE_FACEBOOK: str | None = None
    SOCIAL_PROFILE_TWITTER: str | None = None  # Can be derived from TWITTER_SITE_HANDLE
    SOCIAL_PROFILE_INSTAGRAM: str | None = None
    SOCIAL_PROFILE_LINKEDIN: str | None = None
    SOCIAL_PROFILE_YOUTUBE: str | None = None
    # SOCIAL_PROFILE_PINTEREST: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def __init__(self, **values):
        super().__init__(**values)

        # --- Set conditional defaults after loading from .env and class defaults ---
        if self.EMAILS_FROM_NAME is None:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME

        # SEO related defaults
        if not self.SITE_NAME:
            self.SITE_NAME = self.PROJECT_NAME
        if (
            not self.DEFAULT_META_DESCRIPTION and self.DESCRIPTION
        ):  # Use general DESCRIPTION if meta not set
            self.DEFAULT_META_DESCRIPTION = self.DESCRIPTION
        if not self.CANONICAL_URL_BASE:
            self.CANONICAL_URL_BASE = self.CONTACT_WEBSITE or self.WEB_APP_BASE_URL
        if not self.ORGANIZATION_LEGAL_NAME:
            self.ORGANIZATION_LEGAL_NAME = self.SITE_NAME  # Default legal name to site name

        # --- PostgreSQL URL ---
        if not self.DATABASE_URL and self.POSTGRES_SERVER:
            pg_host_port = self.POSTGRES_SERVER.split(":")
            pg_host = pg_host_port[0]
            pg_port = pg_host_port[1] if len(pg_host_port) > 1 else "5432"  # Default PG port
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

        # --- Redis URLs ---
        if self.REDIS_HOST:  # Only build if REDIS_HOST is set
            effective_redis_scheme = "rediss" if self.REDIS_SSL else "redis"
            valid_cert_reqs_options = ["CERT_REQUIRED", "CERT_OPTIONAL", "CERT_NONE"]
            current_cert_reqs = self.REDIS_SSL_CERT_REQS.upper()

            if self.REDIS_SSL and current_cert_reqs not in valid_cert_reqs_options:
                raise ValueError(
                    f"REDIS_SSL_CERT_REQS (current: {self.REDIS_SSL_CERT_REQS}) "
                    f"must be one of {valid_cert_reqs_options}"
                )

            if not self.REDIS_URL:
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

            if not self.REDIS_URL_CELERY:
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
        if not self.CELERY_BROKER_URL and self.REDIS_URL_CELERY:
            self.CELERY_BROKER_URL = self.REDIS_URL_CELERY
        if not self.CELERY_RESULT_BACKEND_URL and self.REDIS_URL_CELERY:
            self.CELERY_RESULT_BACKEND_URL = self.REDIS_URL_CELERY


settings = Settings()
