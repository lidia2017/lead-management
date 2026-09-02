"""Application configuration, loaded from environment variables.

All settings have dev-friendly defaults so the app runs out of the box, but
every value can be overridden via the environment (see ``.env.example``).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    app_name: str = "Lead Management API"
    environment: str = "development"

    # --- Database ---
    database_url: str = "postgresql+psycopg2://leads:leads@localhost:5432/leads"

    # --- Auth ---
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8

    # Seed attorney (created on startup if the users table is empty).
    seed_attorney_email: str = "attorney@example.com"
    seed_attorney_password: str = "changeme123"
    seed_attorney_name: str = "Alex Attorney"

    # --- File storage ---
    upload_dir: str = "./uploads"
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB
    allowed_resume_types: str = (
        "application/pdf,"
        "application/msword,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "text/plain"
    )

    # --- Email ---
    # Backend selector: "console" | "smtp" | "sendgrid".
    email_backend: str = "console"
    email_from: str = "no-reply@leadmanager.example"
    attorney_notify_email: str = "attorney@example.com"

    # SMTP (used when email_backend == "smtp"; defaults target MailHog).
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = False

    # SendGrid (used when email_backend == "sendgrid").
    sendgrid_api_key: str | None = None

    # --- CORS ---
    cors_origins: str = "http://localhost:3000"

    @property
    def allowed_resume_types_list(self) -> list[str]:
        return [t.strip() for t in self.allowed_resume_types.split(",") if t.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
