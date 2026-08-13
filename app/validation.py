import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.schemas import ExtractedFields, ValidationIssue, ValidationOutcome

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
REFERENCE_RE = re.compile(r"^[A-Z0-9]+(?:-[A-Z0-9]+)+$")
DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y")
REQUIRED_FIELDS = ("document_type", "party_name", "date", "reference_number")


def validate_extraction(data: ExtractedFields) -> ValidationOutcome:
    issues: list[ValidationIssue] = []

    for field in REQUIRED_FIELDS:
        value = getattr(data, field)
        if not value or not value.strip():
            issues.append(_issue(field, "missing_required", "Required value is missing", "required"))

    if data.document_type and data.document_type == "unknown":
        issues.append(_issue("document_type", "unknown_type", "Document type could not be identified", "required"))
    if data.date and not _valid_date(data.date):
        issues.append(_issue("date", "invalid_format", "Use YYYY-MM-DD or DD-MM-YYYY", "required"))
    if data.reference_number and not REFERENCE_RE.fullmatch(data.reference_number.upper()):
        issues.append(
            _issue("reference_number", "invalid_format", "Reference must contain hyphen-separated letters or numbers", "required")
        )
    if data.email and not EMAIL_RE.fullmatch(data.email):
        issues.append(_issue("email", "invalid_format", "Email address format is invalid", "optional"))
    if data.amount and not _valid_amount(data.amount):
        issues.append(_issue("amount", "invalid_amount", "Amount must be a positive numeric value", "optional"))

    if any(issue.severity == "required" for issue in issues):
        status = "rejected"
    elif issues:
        status = "needs_review"
    else:
        status = "approved"
    return ValidationOutcome(status=status, is_valid=not issues, issues=issues)


def _valid_date(value: str) -> bool:
    return any(_parse_date(value, date_format) for date_format in DATE_FORMATS)


def _parse_date(value: str, date_format: str) -> bool:
    try:
        datetime.strptime(value, date_format)
        return True
    except ValueError:
        return False


def _valid_amount(value: str) -> bool:
    try:
        return Decimal(value.replace(",", "")) > 0
    except (InvalidOperation, AttributeError):
        return False


def _issue(field: str, code: str, message: str, severity: str) -> ValidationIssue:
    return ValidationIssue(field=field, code=code, message=message, severity=severity)  # type: ignore[arg-type]

