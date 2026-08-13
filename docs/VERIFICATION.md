# End-to-end verification record

Verified on **2026-08-13** against the Docker Compose stack, not only unit-test mocks.

## Proven live

- Docker image built successfully from `python:3.12-slim`.
- PostgreSQL 16 reached its healthy state and accepted application records.
- Tesseract 5.5.0 and Poppler ran inside the API container.
- The API accepted real PNG, JPG, and PDF multipart uploads.
- Image and PDF documents completed OCR and returned non-empty raw text.
- Extracted values passed through the strict `ExtractedFields` Pydantic schema.
- Deterministic validation produced all three intended outcomes.
- A rejected extraction was corrected through `/documents/{id}/review` and became approved.
- Both the one-call `/documents` workflow and staged `/upload` → `/extract/{id}` → `/validate/{id}` workflow completed.
- PostgreSQL stored document, extraction, and validation rows, including human-review revisions.
- JSON logs recorded upload, OCR, extraction, validation, errors, and final state.
- Unsupported and corrupted uploads returned HTTP 415 and 400 respectively.

| Synthetic document | Expected | Observed |
| --- | --- | --- |
| `invoice_valid.png` | approved | approved |
| `invoice_invalid_email.png` | needs_review | needs_review (`email:invalid_format`) |
| `invoice_missing_reference.png` | rejected | rejected (`reference_number:missing_required`) |
| `receipt_invalid_date.jpg` | rejected | rejected (`date:invalid_format`) |
| `invoice_valid.pdf` | approved | approved after Poppler/Tesseract OCR |

The local regression suite also passed: **19 tests passed**.

## Reproduce

```bash
docker compose up -d --build
python scripts/e2e_smoke.py
pytest -q
```

Inspect persistence and operational logs:

```bash
docker compose exec db psql -U postgres -d docai -c \
  "SELECT status, processing_state, count(*) FROM documents GROUP BY status, processing_state;"
docker compose exec api tail -n 20 /app/logs/app.log
```

## Honest limitation

The verified run used `LLM_MODE=mock`. This mode performs deterministic field extraction but exercises the same Pydantic schema, validation, persistence, logging, error handling, and review path as OpenAI mode.

The OpenAI Responses API adapter and strict Structured Outputs configuration are implemented, but a paid model request was **not** run because no `OPENAI_API_KEY` was configured. Until that is tested, describe the project as having an implemented OpenAI integration—not a live-verified production LLM integration.

