from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import init_db
from app.exceptions import CorruptedFileError, DocumentProcessingError, UnsupportedFileError
from app.logging_config import configure_logging
from app.routes import router


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


@app.exception_handler(UnsupportedFileError)
async def unsupported_file_handler(_: Request, exc: UnsupportedFileError) -> JSONResponse:
    return JSONResponse(status_code=415, content={"error": "unsupported_file", "detail": str(exc)})


@app.exception_handler(CorruptedFileError)
async def corrupted_file_handler(_: Request, exc: CorruptedFileError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": "corrupted_file", "detail": str(exc)})


@app.exception_handler(DocumentProcessingError)
async def processing_error_handler(_: Request, exc: DocumentProcessingError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": type(exc).__name__, "detail": str(exc)})


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(_: Request, __: SQLAlchemyError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"error": "database_unavailable", "detail": "Database operation failed"})


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
