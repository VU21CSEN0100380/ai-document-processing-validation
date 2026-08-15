import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import engine, init_db
from app.exceptions import CorruptedFileError, DocumentProcessingError, UnsupportedFileError
from app.logging_config import configure_logging
from app.ocr import ocr_backend_name
from app.routes import router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    configure_logging(settings.log_dir)
    init_db()
    yield


app = FastAPI(
    title=get_settings().app_name,
    version="1.0.0",
    description="OCR, schema-bound LLM extraction, deterministic validation, and human review.",
    lifespan=lifespan,
)
app.include_router(router)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.exception_handler(UnsupportedFileError)
async def unsupported_file_handler(_: Request, exc: UnsupportedFileError) -> JSONResponse:
    logger.warning("Unsupported upload rejected", extra={"event": "upload_rejected", "error_type": type(exc).__name__})
    return JSONResponse(status_code=415, content={"error": "unsupported_file", "detail": str(exc)})


@app.exception_handler(CorruptedFileError)
async def corrupted_file_handler(_: Request, exc: CorruptedFileError) -> JSONResponse:
    logger.warning("Corrupted upload rejected", extra={"event": "upload_rejected", "error_type": type(exc).__name__})
    return JSONResponse(status_code=400, content={"error": "corrupted_file", "detail": str(exc)})


@app.exception_handler(DocumentProcessingError)
async def processing_error_handler(_: Request, exc: DocumentProcessingError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": type(exc).__name__, "detail": str(exc)})


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database operation failed", extra={"event": "database_failure", "error_type": type(exc).__name__})
    return JSONResponse(status_code=503, content={"error": "database_unavailable", "detail": "Database operation failed"})


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unexpected application error", extra={"event": "unhandled_exception", "error_type": type(exc).__name__})
    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": "Unexpected application error"})


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["system"])
def readiness(response: Response) -> dict[str, object]:
    settings = get_settings()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_ok = True
    except SQLAlchemyError:
        database_ok = False
        response.status_code = 503

    ocr_backend = ocr_backend_name(settings.ocr_mode, settings.tesseract_cmd)
    ocr_available = ocr_backend != "unavailable"
    ephemeral_database = settings.database_url.startswith("sqlite") and settings.is_vercel
    return {
        "status": "ready" if database_ok else "unavailable",
        "environment": "vercel" if settings.is_vercel else settings.app_env,
        "database": "ok" if database_ok else "unavailable",
        "persistence": "ephemeral" if ephemeral_database else "persistent",
        "ocr_backend": ocr_backend,
        "full_pipeline_ready": database_ok and ocr_available and not ephemeral_database,
    }
