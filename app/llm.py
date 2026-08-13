import json
import re
from abc import ABC, abstractmethod

from openai import APITimeoutError, OpenAI
from pydantic import ValidationError

from app.config import Settings
from app.exceptions import LLMExtractionError, LLMTimeoutError, MalformedLLMOutputError
from app.schemas import ExtractedFields


def parse_model_json(payload: str) -> ExtractedFields:
    try:
        return ExtractedFields.model_validate(json.loads(payload))
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise MalformedLLMOutputError("Model output did not match the extraction schema") from exc


class Extractor(ABC):
    @abstractmethod
    def extract(self, raw_text: str) -> ExtractedFields:
        raise NotImplementedError


class MockExtractor(Extractor):
    """Deterministic local extractor for demos and tests; no network calls."""

    def extract(self, raw_text: str) -> ExtractedFields:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        lowered = raw_text.lower()
        document_type = next(
            (kind for kind in ("invoice", "receipt", "contract", "purchase_order") if kind.replace("_", " ") in lowered),
            "unknown",
        )
        email = self._match(r"(?im)^\s*(?:email|e-mail)\s*:\s*(\S+)", raw_text, group=1)
        if not email:
            email = self._match(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", raw_text)
        date = self._match(r"\b\d{4}[-/]\d{2}[-/]\d{2}\b|\b\d{2}[-/]\d{2}[-/]\d{4}\b", raw_text)
        reference = self._match(
            r"(?i)\b(?:ref(?:erence)?|invoice|po)\s*(?:no\.?|number|#|:)?\s*([A-Z0-9][A-Z0-9-]{3,})",
            raw_text,
            group=1,
        )
        amount = self._match(r"(?i)(?:USD|EUR|GBP|INR|\$|€|£|₹)\s*([0-9][0-9,]*(?:\.\d{1,2})?)", raw_text, group=1)
        party = self._party_name(lines)
        summary = " ".join(lines[-2:])[:500] if lines else None
        return ExtractedFields(
            document_type=document_type,
            party_name=party,
            date=date,
            amount=amount.replace(",", "") if amount else None,
            email=email,
            reference_number=reference,
            summary=summary,
        )

    @staticmethod
    def _match(pattern: str, text: str, group: int = 0) -> str | None:
        match = re.search(pattern, text)
        return match.group(group) if match else None

    @staticmethod
    def _party_name(lines: list[str]) -> str | None:
        labels = ("invoice", "receipt", "contract", "date", "email", "ref", "amount", "total")
        return next((line[:200] for line in lines if not line.lower().startswith(labels)), None)


class OpenAIExtractor(Extractor):
    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise LLMExtractionError("OPENAI_API_KEY is required when LLM_MODE=openai")
        self.model = settings.openai_model
        self.client = OpenAI(api_key=settings.openai_api_key, timeout=settings.openai_timeout_seconds)

    def extract(self, raw_text: str) -> ExtractedFields:
        try:
            response = self.client.responses.create(
                model=self.model,
                store=False,
                input=[
                    {
                        "role": "system",
                        "content": "Extract document fields faithfully. Use null when a value is absent; never invent values.",
                    },
                    {"role": "user", "content": f"OCR text:\n\n{raw_text}"},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "document_extraction",
                        "schema": ExtractedFields.model_json_schema(),
                        "strict": True,
                    }
                },
            )
        except APITimeoutError as exc:
            raise LLMTimeoutError("The LLM request timed out") from exc
        except Exception as exc:
            raise LLMExtractionError("The LLM request failed") from exc
        return parse_model_json(response.output_text)


def get_extractor(settings: Settings) -> Extractor:
    if settings.llm_mode.lower() == "mock":
        return MockExtractor()
    if settings.llm_mode.lower() == "openai":
        return OpenAIExtractor(settings)
    raise LLMExtractionError(f"Unsupported LLM_MODE: {settings.llm_mode}")
