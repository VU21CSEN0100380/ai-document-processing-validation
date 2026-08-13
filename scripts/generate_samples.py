"""Generate synthetic OCR fixtures. Every name and identifier is fictional."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "sample_docs"
FONT_CANDIDATES = (
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
)

SAMPLES = {
    "invoice_valid.png": [
        "NORTHSTAR DEMO SERVICES",
        "INVOICE",
        "REFERENCE: INV-2026-001",
        "DATE: 2026-08-13",
        "EMAIL: billing@northstar.example",
        "USD 249.99",
        "Synthetic professional services invoice.",
    ],
    "invoice_invalid_email.png": [
        "BLUE RIVER TEST COMPANY",
        "INVOICE",
        "REFERENCE: INV-2026-002",
        "DATE: 2026-08-13",
        "EMAIL: billing-at-blue-river",
        "USD 125.00",
        "Intentional optional-field validation failure.",
    ],
    "invoice_missing_reference.png": [
        "CEDAR LABS SAMPLE LLC",
        "INVOICE",
        "DATE: 2026-08-13",
        "EMAIL: accounts@cedarlabs.example",
        "USD 88.40",
        "Intentional missing required reference.",
    ],
    "receipt_invalid_date.jpg": [
        "ORBITAL DEMO MARKET",
        "RECEIPT",
        "REFERENCE: REC-2026-004",
        "DATE: 2026-99-45",
        "EMAIL: receipts@orbital.example",
        "USD 42.75",
        "Intentional malformed required date.",
    ],
    "invoice_valid.pdf": [
        "NORTHSTAR DEMO SERVICES",
        "INVOICE",
        "REFERENCE: INV-2026-005",
        "DATE: 2026-08-13",
        "EMAIL: billing@northstar.example",
        "USD 310.50",
        "Synthetic PDF services invoice.",
    ],
}


def font(size: int):
    path = next((candidate for candidate in FONT_CANDIDATES if candidate.exists()), None)
    return ImageFont.truetype(str(path), size) if path else ImageFont.load_default()


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for filename, lines in SAMPLES.items():
        image = Image.new("RGB", (1400, 900), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((55, 55, 1345, 845), outline="#1f2937", width=4)
        y = 105
        for index, line in enumerate(lines):
            draw.text((110, y), line, fill="#111827", font=font(48 if index == 0 else 38))
            y += 95
        image.save(OUTPUT / filename, quality=95)


if __name__ == "__main__":
    main()

