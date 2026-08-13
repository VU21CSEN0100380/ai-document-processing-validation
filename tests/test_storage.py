import pytest

from app.exceptions import CorruptedFileError, UnsupportedFileError
from app.storage import validate_upload


def test_rejects_unsupported_file() -> None:
    with pytest.raises(UnsupportedFileError):
        validate_upload("notes.txt", "text/plain", b"hello", 1024)


def test_rejects_spoofed_pdf() -> None:
    with pytest.raises(CorruptedFileError):
        validate_upload("fake.pdf", "application/pdf", b"not a pdf", 1024)


def test_accepts_png_signature() -> None:
    assert validate_upload("scan.png", "image/png", b"\x89PNG\r\n\x1a\nrest", 1024) == ".png"

