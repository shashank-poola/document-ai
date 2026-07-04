import re
from datetime import datetime

from app.config import get_settings
from app.schemas.enums import ValidationStatus
from app.schemas.extraction import ExtractionResult
from app.schemas.validation import FieldValidation, ValidationResult

ISO_CURRENCIES = frozenset({"USD", "EUR", "GBP", "INR", "JPY", "CAD", "AUD"})
SYMBOL_TO_CURRENCY = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR"}
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y", "%d.%m.%Y")


def _parse_amount(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = re.sub(r"[^\d.]", "", value.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _validate_currency(value: str | None) -> FieldValidation:
    if not value:
        return FieldValidation(
            field_name="currency",
            value=value,
            confidence=0.0,
            status=ValidationStatus.WARN,
            messages=["Currency not detected"],
        )

    normalized = value.upper()
    if normalized in ISO_CURRENCIES or value in SYMBOL_TO_CURRENCY:
        return FieldValidation(
            field_name="currency",
            value=value,
            confidence=1.0,
            status=ValidationStatus.PASS,
        )

    return FieldValidation(
        field_name="currency",
        value=value,
        confidence=0.5,
        status=ValidationStatus.WARN,
        messages=[f"Non-standard currency code: {value}"],
    )


def _validate_date(field_name: str, value: str | None) -> FieldValidation:
    if not value:
        return FieldValidation(
            field_name=field_name,
            value=value,
            confidence=0.0,
            status=ValidationStatus.WARN,
            messages=["Date not detected"],
        )

    parsed = _parse_date(value)
    if parsed:
        return FieldValidation(
            field_name=field_name,
            value=value,
            confidence=1.0,
            status=ValidationStatus.PASS,
        )

    return FieldValidation(
        field_name=field_name,
        value=value,
        confidence=0.3,
        status=ValidationStatus.WARN,
        messages=["Date format could not be parsed"],
    )


def _validate_required(field_name: str, value: str | None) -> FieldValidation:
    if value:
        return FieldValidation(
            field_name=field_name,
            value=value,
            confidence=0.9,
            status=ValidationStatus.PASS,
        )
    return FieldValidation(
        field_name=field_name,
        value=value,
        confidence=0.0,
        status=ValidationStatus.FAIL,
        messages=[f"Required field missing: {field_name}"],
    )


class ValidationService:
    def __init__(self) -> None:
        self._threshold = get_settings().review_confidence_threshold

    def run(self, extractions: list[ExtractionResult]) -> list[ValidationResult]:
        return [self._validate_extraction(item) for item in extractions]

    def _validate_extraction(self, extraction: ExtractionResult) -> ValidationResult:
        field_map = extraction.fields.model_dump()
        validations: list[FieldValidation] = []

        for field_name, value in field_map.items():
            if field_name.endswith("_date") or field_name == "due_date" or field_name == "delivery_date":
                validations.append(_validate_date(field_name, value))
            elif field_name == "currency":
                validations.append(_validate_currency(value))
            elif field_name in {"total", "invoice_number", "po_number", "receipt_number"}:
                validations.append(_validate_required(field_name, value))
            elif value:
                validations.append(
                    FieldValidation(
                        field_name=field_name,
                        value=value,
                        confidence=0.8,
                        status=ValidationStatus.PASS,
                    )
                )

        validations.extend(self._cross_field_checks(field_map))

        confidences = [item.confidence for item in validations if item.confidence > 0]
        overall = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
        overall = round((overall + extraction.extraction_confidence) / 2, 4)

        has_failures = any(item.status == ValidationStatus.FAIL for item in validations)

        return ValidationResult(
            segment_id=extraction.segment_id,
            overall_confidence=overall,
            needs_review=overall < self._threshold or has_failures,
            field_validations=validations,
        )

    @staticmethod
    def _cross_field_checks(field_map: dict[str, str | None]) -> list[FieldValidation]:
        validations: list[FieldValidation] = []
        subtotal = _parse_amount(field_map.get("subtotal"))
        tax = _parse_amount(field_map.get("tax"))
        total = _parse_amount(field_map.get("total"))

        if subtotal is not None and tax is not None and total is not None:
            expected = round(subtotal + tax, 2)
            delta = abs(expected - total)
            if delta <= 1.0:
                validations.append(
                    FieldValidation(
                        field_name="total_calculation",
                        value=str(total),
                        confidence=1.0,
                        status=ValidationStatus.PASS,
                        messages=["Subtotal + tax matches total"],
                    )
                )
            else:
                validations.append(
                    FieldValidation(
                        field_name="total_calculation",
                        value=str(total),
                        confidence=0.3,
                        status=ValidationStatus.WARN,
                        messages=[f"Total mismatch: expected {expected}, found {total}"],
                    )
                )

        return validations
