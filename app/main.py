from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title=get_settings().app_name,
    version="1.0.0",
    description="OCR, schema-bound LLM extraction, deterministic validation, and human review.",
    lifespan=lifespan,
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}

