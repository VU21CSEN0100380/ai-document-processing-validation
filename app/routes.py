import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Document
from app.schemas import DocumentResponse, ReviewRequest, UploadResponse
from app.service import (
    extract_document,
    get_document,
    latest_extraction,
    review_document,
    serialize_document,
    validate_document,
)
from app.storage import save_upload

router = APIRouter()
logger = logging.getLogger(__name__)


async def _create_document(upload: UploadFile, db: Session) -> Document:
    settings = get_settings()
    path, size = await save_upload(upload, settings.upload_dir, settings.max_upload_bytes)
    document = Document(
        filename=upload.filename or path.name,
        stored_path=str(path),
        content_type=upload.content_type or "application/octet-stream",
        size_bytes=size,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    logger.info("Document uploaded", extra={"event": "upload", "document_id": document.id, "status": "uploaded"})
    return document


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED, tags=["processing"])
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)) -> UploadResponse:
    document = await _create_document(file, db)
    return UploadResponse.model_validate(document, from_attributes=True)


@router.post("/extract/{document_id}", response_model=DocumentResponse, tags=["processing"])
def run_extraction(document_id: str, db: Session = Depends(get_db)) -> DocumentResponse:
    document = _require_document(db, document_id)
    extract_document(db, document, get_settings())
    return serialize_document(db, document)


@router.post("/validate/{document_id}", response_model=DocumentResponse, tags=["processing"])
def run_validation(document_id: str, db: Session = Depends(get_db)) -> DocumentResponse:
    document = _require_document(db, document_id)
    extraction = latest_extraction(db, document.id)
    if not extraction:
        raise HTTPException(status_code=409, detail="Run extraction before validation")
    validate_document(db, document, extraction)
    return serialize_document(db, document)


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED, tags=["documents"])
async def process_document(file: UploadFile = File(...), db: Session = Depends(get_db)) -> DocumentResponse:
    document = await _create_document(file, db)
    extraction = extract_document(db, document, get_settings())
    validate_document(db, document, extraction)
    return serialize_document(db, document)


@router.get("/documents/{document_id}", response_model=DocumentResponse, tags=["documents"])
def read_document(document_id: str, db: Session = Depends(get_db)) -> DocumentResponse:
    return serialize_document(db, _require_document(db, document_id))


@router.post("/documents/{document_id}/review", response_model=DocumentResponse, tags=["review"])
def submit_review(document_id: str, request: ReviewRequest, db: Session = Depends(get_db)) -> DocumentResponse:
    document = _require_document(db, document_id)
    review_document(db, document, request)
    return serialize_document(db, document)


def _require_document(db: Session, document_id: str) -> Document:
    document = get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

