from app.schemas.ocr import OCRPageResult
from app.schemas.segment import DocumentSegment
from app.utils.logging import get_logger

logger = get_logger(__name__)


class PassthroughBoundaryDetector:
    """Phase 1–2 boundary detector: treats the entire file as one logical document.

    Phase 3 will replace this with multi-document boundary detection.
    """

    def detect(self, ocr_results: list[OCRPageResult]) -> list[DocumentSegment]:
        if not ocr_results:
            return []

        page_numbers = [result.page_number for result in ocr_results]
        segment = DocumentSegment(
            segment_id="segment_001",
            page_start=min(page_numbers),
            page_end=max(page_numbers),
            boundary_confidence=1.0,
        )
        logger.info(
            "boundary_detection_passthrough",
            page_start=segment.page_start,
            page_end=segment.page_end,
        )
        return [segment]
