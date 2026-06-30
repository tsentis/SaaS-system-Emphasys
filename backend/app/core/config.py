"""Application configuration, loaded from environment variables / .env."""

from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # General
    environment: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me"

    # Database
    postgres_user: str = "emphasys"
    postgres_password: str = "change-me-in-prod"
    postgres_db: str = "emphasys"
    postgres_host: str = "db"
    postgres_port: int = 5432
    database_url: str | None = None  # explicit override wins

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"

    # Object storage
    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "emphasys-documents"
    s3_region: str = "eu-central-1"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_extraction_model: str = "claude-opus-4-8"
    anthropic_bulk_model: str = "claude-sonnet-4-6"

    # Auth (Clerk)
    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""

    # CORS
    cors_origins: str = "http://localhost:3000"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
