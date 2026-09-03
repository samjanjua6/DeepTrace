"""
DeepTrace — Application Settings
All configuration is read from environment variables (or .env via python-dotenv).
pydantic-settings validates types and provides IDE autocompletion.
"""

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    app_secret_key: str = Field(min_length=32)
    app_debug: bool = False
    app_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str

    # ── Redis ────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── Object Storage ───────────────────────────────────────────────────────
    s3_endpoint_url: str | None = None  # None = real AWS S3
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket_documents: str = "deeptrace-documents"
    s3_bucket_artifacts: str = "deeptrace-artifacts"
    s3_region: str = "ap-south-1"

    # ── JWT ──────────────────────────────────────────────────────────────────
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 30

    # ── API Keys ─────────────────────────────────────────────────────────────
    api_key_prefix: str = "dt_pk_"

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: str | list[str] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="after")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ── LLM Providers ────────────────────────────────────────────────────────
    google_gemini_api_key: str | None = None
    anthropic_api_key: str | None = None

    # ── Langfuse Observability ───────────────────────────────────────────────
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    # ── Feature Flags ────────────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Returns a cached Settings instance. Use as a FastAPI dependency."""
    return Settings()
