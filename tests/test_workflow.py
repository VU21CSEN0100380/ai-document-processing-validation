from io import BytesIO
from types import SimpleNamespace

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


def _client(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def override_db():
        with Session(engine) as session:
            yield session

    get_settings().upload_dir = tmp_path
    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def test_end_to_end_processing_and_human_review(tmp_path, monkeypatch) -> None:
    raw_text = (
        "ACME TECHNOLOGIES\nINVOICE\nDATE: 2026-08-13\n"
        "EMAIL: billing@acme.example\nUSD 249.99\nProfessional services"
    )
    monkeypatch.setattr(
        "app.service.get_ocr_backend",
        lambda mode, command: SimpleNamespace(extract=lambda path: raw_text),
    )
    client = _client(tmp_path)
    try:
        processed = client.post("/documents", files={"file": ("invoice.png", _png(), "image/png")})
        assert processed.status_code == 201
        assert processed.json()["status"] == "rejected"
        document_id = processed.json()["id"]

        review = client.post(
            f"/documents/{document_id}/review",
            json={
                "reviewer": "quality@example.test",
                "approve": True,
                "corrected_fields": {
                    "document_type": "invoice",
                    "party_name": "ACME TECHNOLOGIES",
                    "date": "2026-08-13",
                    "amount": "249.99",
                    "email": "billing@acme.example",
                    "reference_number": "INV-2026-001",
                    "summary": "Professional services",
                },
            },
        )
        assert review.status_code == 200
        assert review.json()["status"] == "approved"
        assert review.json()["extracted_data"]["reference_number"] == "INV-2026-001"
    finally:
        app.dependency_overrides.clear()

