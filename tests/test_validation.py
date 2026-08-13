from app.schemas import ExtractedFields
from app.validation import validate_extraction


def fields(**overrides: str | None) -> ExtractedFields:
    values = {
        "document_type": "invoice",
        "party_name": "ACME TECHNOLOGIES",
        "date": "2026-08-13",
        "amount": "249.99",
        "email": "billing@acme.example",
        "reference_number": "INV-2026-001",
        "summary": "Professional services invoice.",
    }
    values.update(overrides)
    return ExtractedFields(**values)


def test_valid_extraction_is_approved() -> None:
    outcome = validate_extraction(fields())
    assert outcome.status == "approved"
    assert outcome.is_valid is True


def test_invalid_email_needs_review() -> None:
    outcome = validate_extraction(fields(email="not-an-email"))
    assert outcome.status == "needs_review"
    assert outcome.issues[0].field == "email"


def test_invalid_date_is_rejected() -> None:
    outcome = validate_extraction(fields(date="2026-99-45"))
    assert outcome.status == "rejected"
    assert any(issue.field == "date" for issue in outcome.issues)


def test_missing_required_field_is_rejected() -> None:
    outcome = validate_extraction(fields(reference_number=None))
    assert outcome.status == "rejected"
    assert any(issue.code == "missing_required" for issue in outcome.issues)


def test_invalid_optional_amount_needs_review() -> None:
    assert validate_extraction(fields(amount="free")).status == "needs_review"

