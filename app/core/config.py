from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


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
    openrouter_codegen_model: str | None = "anthropic/claude-sonnet-4.5"
    openrouter_timeout_seconds: int = Field(default=60, ge=1)

    default_output_format: str = "docx"
    default_language: str = "ru"
    default_style: str = "business"
    default_tone: str = "neutral"
    default_font_family: str = "Times New Roman"
    default_font_size: int = Field(default=12, ge=1)

    public_base_url: str = "http://localhost:8000"
    api_internal_token: SecretStr | None = None

    worker_enabled: bool = True
    worker_concurrency: int = Field(default=1, ge=1)
    worker_poll_interval_seconds: float = Field(default=0.2, ge=0.01)

    docx_codegen_enabled: bool = True
    docx_codegen_fallback_enabled: bool = True
    docx_codegen_image: str = "text-to-doc-builder-docx-runtime:local"
    docx_codegen_timeout_seconds: int = Field(default=30, ge=1)
    docx_codegen_memory_limit: str = "256m"
    docx_codegen_cpu_limit: float = Field(default=1.0, gt=0)
    docx_validation_enabled: bool = True
    docx_codegen_repair_attempts: int = Field(default=1, ge=0, le=3)

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
