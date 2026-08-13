from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.exceptions import CorruptedFileError, UnsupportedFileError

ALLOWED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}
ALLOWED_SUFFIXES = {".pdf", ".jpg", ".jpeg", ".png"}


def validate_upload(filename: str | None, content_type: str | None, data: bytes, max_bytes: int) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES or content_type not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedFileError("Only PDF, JPG, and PNG files are supported")
    if not data:
        raise CorruptedFileError("The uploaded file is empty")
    if len(data) > max_bytes:
        raise CorruptedFileError(f"File exceeds the {max_bytes}-byte upload limit")

    signatures = {
        ".pdf": data.startswith(b"%PDF-"),
        ".jpg": data.startswith(b"\xff\xd8\xff"),
        ".jpeg": data.startswith(b"\xff\xd8\xff"),
        ".png": data.startswith(b"\x89PNG\r\n\x1a\n"),
    }
    if not signatures[suffix]:
        raise CorruptedFileError("File contents do not match the declared format")
    return suffix


async def save_upload(upload: UploadFile, destination: Path, max_bytes: int) -> tuple[Path, int]:
    data = await upload.read(max_bytes + 1)
    suffix = validate_upload(upload.filename, upload.content_type, data, max_bytes)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"{uuid4().hex}{suffix}"
    path.write_bytes(data)
    return path, len(data)

