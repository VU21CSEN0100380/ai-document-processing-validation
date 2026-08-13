import pytest

from app.exceptions import MalformedLLMOutputError
from app.llm import MockExtractor, parse_model_json


def test_mock_extractor_returns_valid_schema() -> None:
    result = MockExtractor().extract(
        "ACME TECHNOLOGIES\nINVOICE REF: INV-2026-001\nDATE: 2026-08-13\n"
        "EMAIL: billing@acme.example\nUSD 249.99\nProfessional services"
    )
    assert result.document_type == "invoice"
    assert result.party_name == "ACME TECHNOLOGIES"
    assert result.reference_number == "INV-2026-001"
    assert result.amount == "249.99"


def test_invoice_heading_does_not_consume_next_line_as_reference() -> None:
    result = MockExtractor().extract(
        "ACME TECHNOLOGIES\nINVOICE\nREFERENCE: INV-2026-001\nDATE: 2026-08-13"
    )
    assert result.reference_number == "INV-2026-001"


def test_missing_reference_stays_missing_across_lines() -> None:
    result = MockExtractor().extract(
        "ACME TECHNOLOGIES\nINVOICE\nDATE: 2026-08-13\nEMAIL: billing@acme.example"
    )
    assert result.reference_number is None


@pytest.mark.parametrize("payload", ["not json", '{"document_type":"invoice"}', "[]"])
def test_malformed_llm_json_is_rejected(payload: str) -> None:
    with pytest.raises(MalformedLLMOutputError):
        parse_model_json(payload)

