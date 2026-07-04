import re
from abc import ABC, abstractmethod

from app.schemas.enums import DocumentType
from app.schemas.extraction import (
    ExtractionResult,
    InvoiceFields,
    PurchaseOrderFields,
    ReceiptFields,
)
from app.schemas.segment import DocumentSegment

DATE_PATTERN = re.compile(
    r"\b(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2})\b"
)
CURRENCY_PATTERN = re.compile(r"\b(USD|EUR|GBP|INR|JPY|CAD|AUD|\$|€|£|₹)\b", re.IGNORECASE)
AMOUNT_PATTERN = re.compile(r"(?:total|amount|subtotal|tax)[:\s]*([₹$€£]?\s?[\d,]+\.?\d*)", re.IGNORECASE)
INVOICE_NUMBER_PATTERN = re.compile(
    r"(?:invoice\s*(?:no|number|#)?[:\s]*)([A-Z0-9\-/]+)",
    re.IGNORECASE,
)
RECEIPT_NUMBER_PATTERN = re.compile(
    r"(?:receipt\s*(?:no|number|#)?[:\s]*)([A-Z0-9\-/]+)",
    re.IGNORECASE,
)
PO_NUMBER_PATTERN = re.compile(
    r"(?:purchase\s*order|po)\s*(?:no|number|#)?[:\s]*([A-Z0-9\-/]+)",
    re.IGNORECASE,
)
VENDOR_PATTERN = re.compile(
    r"(?:from|vendor|seller|supplier)[:\s]+(.+)",
    re.IGNORECASE,
)
BUYER_PATTERN = re.compile(
    r"(?:bill\s*to|buyer|customer|sold\s*to)[:\s]+(.+)",
    re.IGNORECASE,
)


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, segment: DocumentSegment, text: str) -> ExtractionResult:
        """Extract structured fields from OCR text."""


def _first_match(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def _first_date(text: str) -> str | None:
    match = DATE_PATTERN.search(text)
    return match.group(1) if match else None


def _confidence_from_fields(**fields: str | None) -> float:
    populated = sum(1 for value in fields.values() if value)
    total = len(fields)
    return round(populated / total, 4) if total else 0.0


class InvoiceExtractor(BaseExtractor):
    def extract(self, segment: DocumentSegment, text: str) -> ExtractionResult:
        fields = InvoiceFields(
            invoice_number=_first_match(INVOICE_NUMBER_PATTERN, text),
            invoice_date=_first_date(text),
            vendor_name=_first_match(VENDOR_PATTERN, text),
            buyer_name=_first_match(BUYER_PATTERN, text),
            currency=_first_match(CURRENCY_PATTERN, text),
            subtotal=_extract_labeled_amount(text, "subtotal"),
            tax=_extract_labeled_amount(text, "tax"),
            total=_extract_labeled_amount(text, "total"),
            due_date=_extract_labeled_amount(text, "due") or _second_date(text),
        )
        confidence = _confidence_from_fields(**fields.model_dump())
        return ExtractionResult(
            segment_id=segment.segment_id,
            document_type=DocumentType.INVOICE,
            fields=fields,
            raw_text=text,
            extraction_confidence=confidence,
        )


class ReceiptExtractor(BaseExtractor):
    def extract(self, segment: DocumentSegment, text: str) -> ExtractionResult:
        fields = ReceiptFields(
            receipt_number=_first_match(RECEIPT_NUMBER_PATTERN, text),
            receipt_date=_first_date(text),
            merchant_name=_first_match(VENDOR_PATTERN, text),
            currency=_first_match(CURRENCY_PATTERN, text),
            subtotal=_extract_labeled_amount(text, "subtotal"),
            tax=_extract_labeled_amount(text, "tax"),
            total=_extract_labeled_amount(text, "total"),
            payment_method=_first_match(
                re.compile(r"(?:payment\s*method|paid\s*via)[:\s]+(.+)", re.IGNORECASE),
                text,
            ),
        )
        confidence = _confidence_from_fields(**fields.model_dump())
        return ExtractionResult(
            segment_id=segment.segment_id,
            document_type=DocumentType.RECEIPT,
            fields=fields,
            raw_text=text,
            extraction_confidence=confidence,
        )


class PurchaseOrderExtractor(BaseExtractor):
    def extract(self, segment: DocumentSegment, text: str) -> ExtractionResult:
        fields = PurchaseOrderFields(
            po_number=_first_match(PO_NUMBER_PATTERN, text),
            po_date=_first_date(text),
            vendor_name=_first_match(VENDOR_PATTERN, text),
            buyer_name=_first_match(BUYER_PATTERN, text),
            currency=_first_match(CURRENCY_PATTERN, text),
            total=_extract_labeled_amount(text, "total"),
            delivery_date=_second_date(text),
        )
        confidence = _confidence_from_fields(**fields.model_dump())
        return ExtractionResult(
            segment_id=segment.segment_id,
            document_type=DocumentType.PURCHASE_ORDER,
            fields=fields,
            raw_text=text,
            extraction_confidence=confidence,
        )


def _extract_labeled_amount(text: str, label: str) -> str | None:
    pattern = re.compile(rf"{label}[:\s]*([₹$€£]?\s?[\d,]+\.?\d*)", re.IGNORECASE)
    return _first_match(pattern, text)


def _second_date(text: str) -> str | None:
    matches = DATE_PATTERN.findall(text)
    return matches[1] if len(matches) > 1 else None
