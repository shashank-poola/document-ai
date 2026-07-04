import pytest

from app.classification.heuristics import HeuristicClassifier
from app.schemas.enums import DocumentType
from app.schemas.ocr import OCRPageResult
from app.schemas.segment import DocumentSegment


@pytest.fixture
def invoice_segment() -> DocumentSegment:
    return DocumentSegment(segment_id="segment_001", page_start=1, page_end=1)


@pytest.fixture
def invoice_ocr() -> list[OCRPageResult]:
    text = """
    TAX INVOICE
    Invoice No: INV-1002
    Date: 02/06/2026
    Vendor: ABC Pvt Ltd
    Bill To: XYZ Corp
    Subtotal: 20,000
    Tax: 4,550
    Total: 24,550 INR
    """
    return [OCRPageResult(page_number=1, full_text=text, average_confidence=0.95)]


def test_classifies_invoice(invoice_segment: DocumentSegment, invoice_ocr: list[OCRPageResult]) -> None:
    classifier = HeuristicClassifier()
    result = classifier.classify_segment(invoice_segment, invoice_ocr)

    assert result.document_type == DocumentType.INVOICE
    assert result.classification_confidence > 0


def test_extracts_invoice_fields(invoice_segment: DocumentSegment, invoice_ocr: list[OCRPageResult]) -> None:
    from app.extraction.extractors import InvoiceExtractor

    extractor = InvoiceExtractor()
    text = invoice_ocr[0].full_text
    invoice_segment.document_type = DocumentType.INVOICE

    result = extractor.extract(invoice_segment, text)

    assert result.fields.invoice_number == "INV-1002"
    assert result.fields.vendor_name is not None
    assert result.extraction_confidence > 0


def test_validates_invoice_totals(invoice_segment: DocumentSegment, invoice_ocr: list[OCRPageResult]) -> None:
    from app.extraction.extractors import InvoiceExtractor
    from app.validation import ValidationService

    invoice_segment.document_type = DocumentType.INVOICE
    extraction = InvoiceExtractor().extract(invoice_segment, invoice_ocr[0].full_text)
    validation = ValidationService().run([extraction])[0]

    assert validation.overall_confidence > 0
    assert any(item.field_name == "total_calculation" for item in validation.field_validations)
