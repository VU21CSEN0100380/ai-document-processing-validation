from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DocumentStatus = Literal["uploaded", "approved", "needs_review", "rejected", "failed"]
ProcessingState = Literal["uploaded", "ocr_complete", "extraction_complete", "validated", "failed"]


class ExtractedFields(BaseModel):
    """Strict contract shared by LLM output, persistence, and review input."""

    model_config = ConfigDict(extra="forbid")

    document_type: str | None
    party_name: str | None
    date: str | None
    amount: str | None
    email: str | None
    reference_number: str | None
    summary: str | None


class ValidationIssue(BaseModel):
    field: str
    code: str
    message: str
    severity: Literal["required", "optional"]


class ValidationOutcome(BaseModel):
    status: Literal["approved", "needs_review", "rejected"]
    is_valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)


class UploadResponse(BaseModel):
    id: str
    filename: str
    status: DocumentStatus
    processing_state: ProcessingState


class DocumentResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    status: DocumentStatus
    processing_state: ProcessingState
    raw_text: str | None = None
    extracted_data: dict[str, Any] | None = None
    validation_errors: list[dict[str, Any]] = Field(default_factory=list)
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class ReviewRequest(BaseModel):
    corrected_fields: ExtractedFields
    reviewer: str = Field(min_length=1, max_length=120)
    approve: bool = True

