from pathlib import Path

import pytesseract
from pdf2image import convert_from_path
from PIL import Image, UnidentifiedImageError

from app.exceptions import CorruptedFileError, OCRProcessingError


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
