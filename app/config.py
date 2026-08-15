import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _on_vercel() -> bool:
    return bool(os.getenv("VERCEL"))


def _default_database_url() -> str:
    return "sqlite:////tmp/docai.db" if _on_vercel() else "sqlite:///./docai.db"


def _default_runtime_dir(name: str) -> Path:
    return Path("/tmp") / name if _on_vercel() else Path(name)


def _default_ocr_mode() -> str:
    return "rapidocr" if _on_vercel() else "tesseract"


class Settings(BaseSettings):
    app_name: str = "AI Document Processing & Validation API"
    app_env: str = "development"
    database_url: str = Field(default_factory=_default_database_url)
    upload_dir: Path = Field(default_factory=lambda: _default_runtime_dir("uploads"))
    log_dir: Path = Field(default_factory=lambda: _default_runtime_dir("logs"))
    max_upload_bytes: int = 10 * 1024 * 1024
    ocr_mode: str = Field(default_factory=_default_ocr_mode)
    tesseract_cmd: str | None = None
    llm_mode: str = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 30.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if isinstance(value, str) and value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @property
    def is_vercel(self) -> bool:
        return _on_vercel()


@lru_cache
def get_settings() -> Settings:
    return Settings()

