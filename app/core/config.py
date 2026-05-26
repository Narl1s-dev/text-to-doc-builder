from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Text To Doc Builder"
    app_version: str = "0.1.0"
    app_env: str = "local"
    debug: bool = False
    log_level: str = "INFO"

    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = "sqlite:///./storage/app.db"
    artifact_storage_path: Path = Path("./storage/artifacts")

    openrouter_api_key: SecretStr | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str | None = None
    openrouter_timeout_seconds: int = Field(default=60, ge=1)

    default_output_format: str = "docx"
    default_language: str = "ru"
    default_style: str = "business"
    default_tone: str = "neutral"
    default_font_family: str = "Times New Roman"
    default_font_size: int = Field(default=12, ge=1)

    public_base_url: str = "http://localhost:8000"
    api_internal_token: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

