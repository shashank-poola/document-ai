from enum import StrEnum


class JobStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    PREPROCESSING = "preprocessing"
    OCR = "ocr"
    BOUNDARY_DETECTION = "boundary_detection"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    VALIDATION = "validation"
    OUTPUT = "output"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class DocumentType(StrEnum):
    INVOICE = "invoice"
    RECEIPT = "receipt"
    PURCHASE_ORDER = "purchase_order"
    UNKNOWN = "unknown"


class PageSource(StrEnum):
    TEXT_NATIVE = "text_native"
    NEEDS_OCR = "needs_ocr"
    MIXED = "mixed"


class ValidationStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class FileFormat(StrEnum):
    PDF = "pdf"
    IMAGE = "image"
    DOCX = "docx"
