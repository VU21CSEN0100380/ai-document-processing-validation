import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.exceptions import DocumentProcessingError
from app.llm import get_extractor
from app.models import Document, Extraction, ValidationResult
from app.ocr import TesseractOCR
from app.schemas import DocumentResponse, ExtractedFields, ReviewRequest, ValidationOutcome
from app.validation import validate_extraction

logger = logging.getLogger(__name__)


def get_document(db: Session, document_id: str) -> Document | None:
    return db.get(Document, document_id)


def latest_extraction(db: Session, document_id: str) -> Extraction | None:
    return db.scalar(
        select(Extraction).where(Extraction.document_id == document_id).order_by(Extraction.id.desc()).limit(1)
    )


def latest_validation(db: Session, document_id: str) -> ValidationResult | None:
    return db.scalar(
        select(ValidationResult)
        .where(ValidationResult.document_id == document_id)
        .order_by(ValidationResult.id.desc())
        .limit(1)
    )


def extract_document(db: Session, document: Document, settings: Settings) -> Extraction:
    try:
        raw_text = TesseractOCR(settings.tesseract_cmd).extract(Path(document.stored_path))
        document.processing_state = "ocr_complete"
        db.commit()
        logger.info("OCR completed", extra={"event": "ocr_complete", "document_id": document.id})

        extractor = get_extractor(settings)
        logger.info("LLM extraction requested", extra={"event": "llm_request", "document_id": document.id})
        fields = extractor.extract(raw_text)
        extraction = Extraction(
            document_id=document.id,
            raw_text=raw_text,
            extracted_json=fields.model_dump(mode="json"),
            source=settings.llm_mode,
            model_name=settings.openai_model if settings.llm_mode == "openai" else "deterministic-mock",
        )
        db.add(extraction)
        document.processing_state = "extraction_complete"
        db.commit()
        db.refresh(extraction)
        logger.info("LLM extraction completed", extra={"event": "llm_result", "document_id": document.id, "status": "ok"})
        return extraction
    except DocumentProcessingError as exc:
        _mark_failed(db, document, exc)
        raise


def validate_document(db: Session, document: Document, extraction: Extraction) -> ValidationResult:
    fields = ExtractedFields.model_validate(extraction.extracted_json)
    outcome = validate_extraction(fields)
    result = _save_validation(db, document, extraction, outcome)
    if outcome.issues:
        logger.warning(
            "Validation produced issues",
            extra={"event": "validation_failure", "document_id": document.id, "status": outcome.status},
        )
    logger.info(
        "Document processing finalized",
        extra={"event": "processing_complete", "document_id": document.id, "status": outcome.status},
    )
    return result


def review_document(db: Session, document: Document, request: ReviewRequest) -> ValidationResult:
    previous = latest_extraction(db, document.id)
    raw_text = previous.raw_text if previous else ""
    extraction = Extraction(
        document_id=document.id,
        raw_text=raw_text,
        extracted_json=request.corrected_fields.model_dump(mode="json"),
        source="human_review",
        model_name=None,
    )
    db.add(extraction)
    db.flush()
    outcome = validate_extraction(request.corrected_fields)
    if request.approve and outcome.status == "rejected":
        return _save_validation(db, document, extraction, outcome)
    if not request.approve and outcome.status == "approved":
        outcome = ValidationOutcome(status="needs_review", is_valid=True, issues=[])
    document.reviewed_by = request.reviewer
    document.reviewed_at = datetime.now(timezone.utc)
    return _save_validation(db, document, extraction, outcome)


def serialize_document(db: Session, document: Document) -> DocumentResponse:
    extraction = latest_extraction(db, document.id)
    validation = latest_validation(db, document.id)
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        content_type=document.content_type,
        status=document.status,
        processing_state=document.processing_state,
        raw_text=extraction.raw_text if extraction else None,
        extracted_data=extraction.extracted_json if extraction else None,
        validation_errors=validation.errors if validation else [],
        error_message=document.error_message,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _save_validation(
    db: Session, document: Document, extraction: Extraction, outcome: ValidationOutcome
) -> ValidationResult:
    result = ValidationResult(
        document_id=document.id,
        extraction_id=extraction.id,
        status=outcome.status,
        is_valid=outcome.is_valid,
        errors=[issue.model_dump(mode="json") for issue in outcome.issues],
    )
    db.add(result)
    document.status = outcome.status
    document.processing_state = "validated"
    document.error_message = None
    db.commit()
    db.refresh(result)
    return result


def _mark_failed(db: Session, document: Document, exc: Exception) -> None:
    document.status = "failed"
    document.processing_state = "failed"
    document.error_message = str(exc)
    db.commit()
    logger.exception(
        "Document processing failed",
        extra={"event": "processing_exception", "document_id": document.id, "error_type": type(exc).__name__},
    )

