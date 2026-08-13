from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base, get_db
from app.main import app


def _png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (20, 20), "white").save(output, format="PNG")
    return output.getvalue()


def test_unsupported_upload_returns_415() -> None:
    response = TestClient(app).post("/upload", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 415
    assert response.json()["error"] == "unsupported_file"


def test_upload_and_fetch_document(tmp_path) -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)

    def override_db():
        with Session(engine) as session:
            yield session

    settings = get_settings()
    old_upload_dir = settings.upload_dir
    settings.upload_dir = tmp_path
    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        uploaded = client.post("/upload", files={"file": ("invoice.png", _png(), "image/png")})
        assert uploaded.status_code == 201
        payload = uploaded.json()
        assert payload["status"] == "uploaded"

        fetched = client.get(f"/documents/{payload['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["filename"] == "invoice.png"
    finally:
        settings.upload_dir = old_upload_dir
        app.dependency_overrides.clear()

