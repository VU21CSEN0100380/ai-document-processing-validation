from pathlib import Path

import pytest

from app.exceptions import OCRProcessingError
from app.ocr import TesseractOCR


def test_missing_tesseract_is_reported_as_ocr_failure(monkeypatch, tmp_path: Path) -> None:
    image_path = tmp_path / "valid.png"
    image_path.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb1\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    monkeypatch.setattr("app.ocr.pytesseract.image_to_string", lambda image: (_ for _ in ()).throw(Exception()))

    # Exercise the public error contract without depending on a host OCR installation.
    monkeypatch.setattr(
        "app.ocr.pytesseract.image_to_string",
        lambda image: (_ for _ in ()).throw(__import__("pytesseract").TesseractNotFoundError()),
    )
    with pytest.raises(OCRProcessingError):
        TesseractOCR().extract(image_path)

