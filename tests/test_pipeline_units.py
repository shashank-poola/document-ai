import pytest

from app.classification.heuristics import HeuristicClassifier
from app.schemas.enums import DocumentType
from app.schemas.ocr import OCRPageResult
from app.schemas.segment import DocumentSegment

WORDPRESS_INVOICE_TEXT = """Invoice
Payment is due within 30 days from date of invoice. Late payment is subject to fees of 5% per month.
Thanks for choosing DEMO - Sliced Invoices | admin@slicedinvoices.com
Page 1/1
From:
DEMO - Sliced Invoices
Suite 5A-1204
123 Somewhere Street
Your City AZ 12345
admin@slicedinvoices.com
Invoice Number
INV-3337
Order Number
12345
Invoice Date
January 25, 2016
Due Date
January 31, 2016
Total Due
$93.50
To:
Test Business
123 Somewhere St
Melbourne, VIC 3000
test@test.com
Hrs/Qty
Service
Rate/Price
Adjust
Sub Total
1.00
Web Design
This is a sample description...
$85.00
0.00%
$85.00
Sub Total
$85.00
Tax
$8.50
Total
$93.50
ANZ Bank
ACC # 1234 1234
BSB # 4321 432
Paid"""

TCPDF_INVOICE_TEXT = """Invoice #13594027
Description
Total
Sub Total
Credit
USD $0.00
Total
Transactions
Date: 06/23/2018
Your Business Name
Invoiced To
John Smith
USD $50.00
USD $37.50
USD $37.50
USD $-12.50
USD $37.50"""


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


@pytest.fixture
def wordpress_invoice_ocr() -> list[OCRPageResult]:
    return [OCRPageResult(page_number=1, full_text=WORDPRESS_INVOICE_TEXT, average_confidence=1.0)]


def test_classifies_invoice(
    invoice_segment: DocumentSegment,
    invoice_ocr: list[OCRPageResult],
) -> None:
    classifier = HeuristicClassifier()
    result = classifier.classify_segment(invoice_segment, invoice_ocr)

    assert result.document_type == DocumentType.INVOICE
    assert result.classification_confidence > 0


def test_extracts_invoice_fields(
    invoice_segment: DocumentSegment,
    invoice_ocr: list[OCRPageResult],
) -> None:
    from app.extraction.extractors import InvoiceExtractor

    extractor = InvoiceExtractor()
    text = invoice_ocr[0].full_text
    invoice_segment.document_type = DocumentType.INVOICE

    result = extractor.extract(invoice_segment, text)

    assert result.fields.invoice_number == "INV-1002"
    assert result.fields.vendor_name is not None
    assert result.extraction_confidence > 0


def test_extracts_wordpress_invoice_sample(
    invoice_segment: DocumentSegment,
    wordpress_invoice_ocr: list[OCRPageResult],
) -> None:
    from app.extraction.extractors import InvoiceExtractor

    invoice_segment.document_type = DocumentType.INVOICE
    result = InvoiceExtractor().extract(invoice_segment, wordpress_invoice_ocr[0].full_text)

    assert result.fields.invoice_number == "INV-3337"
    assert result.fields.invoice_date == "January 25, 2016"
    assert result.fields.vendor_name == "DEMO - Sliced Invoices"
    assert result.fields.buyer_name == "Test Business"
    assert result.fields.currency == "USD"
    assert result.fields.subtotal == "$85.00"
    assert result.fields.tax == "$8.50"
    assert result.fields.total == "$93.50"
    assert result.fields.due_date == "January 31, 2016"


def test_extracts_tcpdf_invoice_sample(invoice_segment: DocumentSegment) -> None:
    from app.extraction.extractors import InvoiceExtractor

    invoice_segment.document_type = DocumentType.INVOICE
    result = InvoiceExtractor().extract(invoice_segment, TCPDF_INVOICE_TEXT)

    assert result.fields.invoice_number == "13594027"
    assert result.fields.invoice_date == "06/23/2018"
    assert result.fields.vendor_name == "Your Business Name"
    assert result.fields.buyer_name == "John Smith"
    assert result.fields.currency == "USD"
    assert result.fields.subtotal == "USD $37.50"
    assert result.fields.total == "USD $37.50"
    assert result.fields.tax is None


def test_validates_invoice_totals(
    invoice_segment: DocumentSegment,
    invoice_ocr: list[OCRPageResult],
) -> None:
    from app.extraction.extractors import InvoiceExtractor
    from app.validation import ValidationService

    invoice_segment.document_type = DocumentType.INVOICE
    extraction = InvoiceExtractor().extract(invoice_segment, invoice_ocr[0].full_text)
    validation = ValidationService().run([extraction])[0]

    assert validation.overall_confidence > 0
    assert any(item.field_name == "total_calculation" for item in validation.field_validations)


def test_validates_wordpress_invoice_totals(
    invoice_segment: DocumentSegment,
    wordpress_invoice_ocr: list[OCRPageResult],
) -> None:
    from app.extraction.extractors import InvoiceExtractor
    from app.validation import ValidationService

    invoice_segment.document_type = DocumentType.INVOICE
    extraction = InvoiceExtractor().extract(invoice_segment, wordpress_invoice_ocr[0].full_text)
    validation = ValidationService().run([extraction])[0]

    assert validation.overall_confidence >= 0.75
    assert validation.needs_review is False
    assert any(
        item.field_name == "total_calculation" and item.status.value == "pass"
        for item in validation.field_validations
    )
