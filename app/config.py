from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Document Processing & Validation API"
    app_env: str = "development"
    database_url: str = "sqlite:///./docai.db"
    upload_dir: Path = Path("uploads")
    log_dir: Path = Path("logs")
    max_upload_bytes: int = 10 * 1024 * 1024
    tesseract_cmd: str | None = None
    llm_mode: str = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 30.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

