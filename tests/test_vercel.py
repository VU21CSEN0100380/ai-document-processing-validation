from app.config import Settings
from app.main import app
from fastapi.testclient import TestClient


def test_vercel_defaults_use_writable_tmp(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")
    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:////tmp/docai.db"
    assert settings.upload_dir.as_posix() == "/tmp/uploads"
    assert settings.log_dir.as_posix() == "/tmp/logs"
    assert settings.ocr_mode == "rapidocr"
    assert settings.is_vercel is True


def test_postgres_urls_use_psycopg_driver() -> None:
    settings = Settings(_env_file=None, database_url="postgres://user:pass@example.test/db")
    assert settings.database_url == "postgresql+psycopg://user:pass@example.test/db"


def test_root_redirects_to_swagger() -> None:
    response = TestClient(app).get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_readiness_reports_runtime_capabilities() -> None:
    response = TestClient(app).get("/health/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["database"] == "ok"
    assert payload["ocr_backend"] in {"tesseract", "rapidocr", "unavailable"}
    assert isinstance(payload["full_pipeline_ready"], bool)
