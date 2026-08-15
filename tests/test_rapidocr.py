from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from app.ocr import RapidOCROCR


def test_rapidocr_backend_returns_joined_text(monkeypatch, tmp_path: Path) -> None:
    image_path = tmp_path / "document.png"
    Image.new("RGB", (20, 20), "white").save(image_path)
    monkeypatch.setattr(
        "app.ocr._rapidocr_engine",
        lambda: lambda image: SimpleNamespace(txts=("ACME INVOICE", "INV-2026-001")),
    )
    assert RapidOCROCR().extract(image_path) == "ACME INVOICE\nINV-2026-001"
