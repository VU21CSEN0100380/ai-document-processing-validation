"""Exercise the running Docker stack through its public HTTP API."""

import json
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:8000")
SAMPLES = (
    ("invoice_valid.png", "image/png", "approved"),
    ("invoice_invalid_email.png", "image/png", "needs_review"),
    ("invoice_missing_reference.png", "image/png", "rejected"),
    ("receipt_invalid_date.jpg", "image/jpeg", "rejected"),
    ("invoice_valid.pdf", "application/pdf", "approved"),
)


def require(response: httpx.Response, expected_code: int) -> dict:
    if response.status_code != expected_code:
        raise AssertionError(f"{response.request.method} {response.request.url}: {response.status_code} {response.text}")
    return response.json()


def upload(client: httpx.Client, endpoint: str, filename: str, content_type: str) -> dict:
    path = ROOT / "sample_docs" / filename
    with path.open("rb") as handle:
        return require(client.post(endpoint, files={"file": (filename, handle, content_type)}), 201)


def main() -> None:
    evidence: dict[str, object] = {"base_url": BASE_URL, "samples": []}
    with httpx.Client(base_url=BASE_URL, timeout=90) as client:
        assert require(client.get("/health"), 200) == {"status": "ok"}

        rejected_id: str | None = None
        for filename, content_type, expected_status in SAMPLES:
            result = upload(client, "/documents", filename, content_type)
            assert result["status"] == expected_status, (filename, result)
            assert result["processing_state"] == "validated"
            assert result["raw_text"].strip()
            evidence["samples"].append(
                {
                    "filename": filename,
                    "status": result["status"],
                    "reference_number": result["extracted_data"]["reference_number"],
                    "issues": [issue["code"] for issue in result["validation_errors"]],
                }
            )
            if filename == "invoice_missing_reference.png":
                rejected_id = result["id"]

        assert rejected_id
        reviewed = require(
            client.post(
                f"/documents/{rejected_id}/review",
                json={
                    "reviewer": "e2e-smoke@example.test",
                    "approve": True,
                    "corrected_fields": {
                        "document_type": "invoice",
                        "party_name": "CEDAR LABS SAMPLE LLC",
                        "date": "2026-08-13",
                        "amount": "88.40",
                        "email": "accounts@cedarlabs.example",
                        "reference_number": "INV-2026-003",
                        "summary": "Synthetic corrected invoice",
                    },
                },
            ),
            200,
        )
        assert reviewed["status"] == "approved"
        evidence["human_review"] = {"before": "rejected", "after": reviewed["status"]}

        staged = upload(client, "/upload", "invoice_valid.png", "image/png")
        extracted = require(client.post(f"/extract/{staged['id']}"), 200)
        validated = require(client.post(f"/validate/{staged['id']}"), 200)
        assert staged["processing_state"] == "uploaded"
        assert extracted["processing_state"] == "extraction_complete"
        assert validated["status"] == "approved"
        evidence["staged_pipeline"] = ["uploaded", "extraction_complete", "validated"]

        unsupported = client.post("/upload", files={"file": ("notes.txt", b"hello", "text/plain")})
        corrupt = client.post("/upload", files={"file": ("fake.pdf", b"not a pdf", "application/pdf")})
        assert unsupported.status_code == 415
        assert corrupt.status_code == 400
        evidence["error_responses"] = {"unsupported": 415, "corrupted": 400}

    evidence["result"] = "PASS"
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()

