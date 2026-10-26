from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr, model_validator


class Settings(BaseSettings):
    app_name: str = "AppHealth API"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://apphealth:apphealth@localhost:5432/apphealth"
    secret_key: str = "development-only-secret-change-before-deployment"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "apphealth-api"
    jwt_audience: str = "apphealth-android"
    access_token_minutes: int = 30
    refresh_token_days: int = 30
    google_web_client_id: str | None = None
    groq_api_key: SecretStr | None = None
    groq_model: str = "qwen/qwen3.8-27b"
    gemini_api_key: SecretStr | None = None
    max_image_size_mb: int = Field(default=8, ge=1, le=20)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
