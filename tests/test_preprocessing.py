from app.boundary_detection import PassthroughBoundaryDetector
from app.schemas.ocr import OCRPageResult


def test_passthrough_boundary_groups_all_pages() -> None:
    ocr_results = [
        OCRPageResult(page_number=1, full_text="page 1"),
        OCRPageResult(page_number=2, full_text="page 2"),
        OCRPageResult(page_number=3, full_text="page 3"),
    ]

    segments = PassthroughBoundaryDetector().detect(ocr_results)

    assert len(segments) == 1
    assert segments[0].page_start == 1
    assert segments[0].page_end == 3


def test_detect_file_format() -> None:
    from app.preprocessing.detector import detect_file_format
    from app.schemas.enums import FileFormat

    assert detect_file_format("invoice.pdf") == FileFormat.PDF
    assert detect_file_format("scan.png") == FileFormat.IMAGE
    assert detect_file_format("report.docx") == FileFormat.DOCX
