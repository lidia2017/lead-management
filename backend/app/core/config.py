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
    # Connection pool tuning (ignored for SQLite). Each API replica keeps its
    # own small pool; a real deployment fronts Postgres with PgBouncer.
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # --- Redis (broker + rate-limit + idempotency store) ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Auth ---
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8

    # Seed attorney (created on startup if the users table is empty).
    seed_attorney_email: str = "attorney@example.com"
    seed_attorney_password: str = "changeme123"
    seed_attorney_name: str = "Alex Attorney"

    # --- File storage ---
    # Backend selector: "local" | "s3". S3 lets many API replicas share one
    # durable store (and enables direct browser <-> S3 transfers via presigned
    # URLs in a fuller implementation).
    storage_backend: str = "local"
    upload_dir: str = "./uploads"
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB

    # S3 / MinIO (used when storage_backend == "s3").
    s3_bucket: str = "resumes"
    s3_endpoint_url: str | None = None  # e.g. http://minio:9000 for MinIO
    s3_region: str = "us-east-1"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    allowed_resume_types: str = (
        "application/pdf,"
        "application/msword,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "text/plain"
    )

    # --- Email ---
    # Delivery path: "inline" (FastAPI BackgroundTask, single-node/dev/tests)
    # or "celery" (enqueue to a worker pool for durable, retryable delivery).
    email_delivery: str = "inline"
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

    # --- Rate limiting (public submit endpoint) ---
    rate_limit_enabled: bool = False
    rate_limit_public: str = "10/minute"

    # --- Idempotency (public submit) ---
    idempotency_enabled: bool = False
    idempotency_ttl_seconds: int = 24 * 60 * 60

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
