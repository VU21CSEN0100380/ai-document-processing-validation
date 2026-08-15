import importlib.util
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import pytesseract
from pdf2image import convert_from_path
from PIL import Image, UnidentifiedImageError

from app.exceptions import CorruptedFileError, OCRProcessingError


class OCRBackend(Protocol):
    def extract(self, path: Path) -> str: ...


class TesseractOCR:
    def __init__(self, tesseract_cmd: str | None = None) -> None:
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def extract(self, path: Path) -> str:
        try:
            if path.suffix.lower() == ".pdf":
                pages = convert_from_path(path, dpi=300)
                text = "\n\n".join(pytesseract.image_to_string(page) for page in pages)
            else:
                with Image.open(path) as image:
                    image.verify()
                with Image.open(path) as image:
                    text = pytesseract.image_to_string(image)
        except (pytesseract.TesseractError, pytesseract.TesseractNotFoundError) as exc:
            raise OCRProcessingError("Tesseract OCR failed") from exc
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise CorruptedFileError("The document could not be decoded") from exc
        except Exception as exc:
            raise OCRProcessingError("PDF conversion or OCR failed") from exc

        cleaned = text.strip()
        if not cleaned:
            raise OCRProcessingError("OCR produced no text")
        return cleaned


@lru_cache
def _rapidocr_engine():
    from rapidocr import RapidOCR

    return RapidOCR()


class RapidOCROCR:
    """ONNX-based OCR fallback for serverless runtimes without system binaries."""

    def extract(self, path: Path) -> str:
        try:
            images = self._images(path)
            lines: list[str] = []
            engine = _rapidocr_engine()
            for image in images:
                import numpy as np

                result = engine(np.asarray(image.convert("RGB")))
                if result.txts:
                    lines.extend(text.strip() for text in result.txts if text.strip())
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise CorruptedFileError("The document could not be decoded") from exc
        except Exception as exc:
            raise OCRProcessingError("RapidOCR processing failed") from exc

        cleaned = "\n".join(lines).strip()
        if not cleaned:
            raise OCRProcessingError("OCR produced no text")
        return cleaned

    @staticmethod
    def _images(path: Path) -> list[Image.Image]:
        if path.suffix.lower() != ".pdf":
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                return [image.convert("RGB")]

        import pypdfium2 as pdfium

        document = pdfium.PdfDocument(path)
        images: list[Image.Image] = []
        try:
            for page in document:
                bitmap = page.render(scale=300 / 72)
                images.append(bitmap.to_pil().convert("RGB"))
                bitmap.close()
                page.close()
        finally:
            document.close()
        return images


def ocr_backend_name(mode: str, tesseract_cmd: str | None = None) -> str:
    normalized = mode.lower()
    tesseract_available = bool((tesseract_cmd and Path(tesseract_cmd).exists()) or shutil.which("tesseract"))
    rapidocr_available = importlib.util.find_spec("rapidocr") is not None
    if normalized == "tesseract":
        return "tesseract" if tesseract_available else "unavailable"
    if normalized == "rapidocr":
        return "rapidocr" if rapidocr_available else "unavailable"
    if normalized == "auto":
        if tesseract_available:
            return "tesseract"
        if rapidocr_available:
            return "rapidocr"
        return "unavailable"
    return "unavailable"


def get_ocr_backend(mode: str, tesseract_cmd: str | None = None) -> OCRBackend:
    backend = ocr_backend_name(mode, tesseract_cmd)
    if backend == "tesseract":
        return TesseractOCR(tesseract_cmd)
    if backend == "rapidocr":
        return RapidOCROCR()
    raise OCRProcessingError(f"OCR backend '{mode}' is unavailable")
