from app.extraction.extractors import (
    BaseExtractor,
    InvoiceExtractor,
    PurchaseOrderExtractor,
    ReceiptExtractor,
)
from app.schemas.enums import DocumentType
from app.schemas.extraction import ExtractionResult, InvoiceFields
from app.schemas.ocr import OCRPageResult
from app.schemas.segment import DocumentSegment
from app.utils.exceptions import PipelineStageError


class ExtractionService:
    def __init__(self) -> None:
        self._extractors: dict[DocumentType, BaseExtractor] = {
            DocumentType.INVOICE: InvoiceExtractor(),
            DocumentType.RECEIPT: ReceiptExtractor(),
            DocumentType.PURCHASE_ORDER: PurchaseOrderExtractor(),
        }

    def run(
        self,
        segments: list[DocumentSegment],
        ocr_results: list[OCRPageResult],
    ) -> list[ExtractionResult]:
        results: list[ExtractionResult] = []

        for segment in segments:
            text = self._segment_text(segment, ocr_results)
            extractor = self._extractors.get(segment.document_type)

            if extractor is None:
                results.append(self._unknown_result(segment, text))
                continue

            try:
                results.append(extractor.extract(segment, text))
            except Exception as exc:
                raise PipelineStageError("extraction", str(exc)) from exc

        return results

    @staticmethod
    def _segment_text(segment: DocumentSegment, ocr_results: list[OCRPageResult]) -> str:
        pages = {
            result.page_number: result.full_text
            for result in ocr_results
            if segment.page_start <= result.page_number <= segment.page_end
        }
        return "\n\n".join(pages[num] for num in sorted(pages))

    @staticmethod
    def _unknown_result(segment: DocumentSegment, text: str) -> ExtractionResult:
        return ExtractionResult(
            segment_id=segment.segment_id,
            document_type=DocumentType.UNKNOWN,
            fields=InvoiceFields(),
            raw_text=text,
            extraction_confidence=0.0,
        )
