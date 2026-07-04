import re
from dataclasses import dataclass

from app.schemas.enums import DocumentType
from app.schemas.ocr import OCRPageResult
from app.schemas.segment import DocumentSegment

INVOICE_KEYWORDS = ("invoice", "tax invoice", "bill to", "invoice no", "invoice #")
RECEIPT_KEYWORDS = ("receipt", "payment received", "thank you for your purchase")
PO_KEYWORDS = ("purchase order", "po number", "po #", "p.o.")


@dataclass(frozen=True)
class ClassificationScore:
    document_type: DocumentType
    confidence: float
    evidence: list[str]


class HeuristicClassifier:
    """Keyword and pattern-based document type classifier."""

    def classify_segment(
        self,
        segment: DocumentSegment,
        ocr_results: list[OCRPageResult],
    ) -> DocumentSegment:
        segment_text = self._collect_segment_text(segment, ocr_results)
        normalized = segment_text.lower()

        scores = [
            self._score_keywords(normalized, DocumentType.INVOICE, INVOICE_KEYWORDS),
            self._score_keywords(normalized, DocumentType.RECEIPT, RECEIPT_KEYWORDS),
            self._score_keywords(normalized, DocumentType.PURCHASE_ORDER, PO_KEYWORDS),
        ]
        best = max(scores, key=lambda item: item.confidence)

        if best.confidence < 0.3:
            best = ClassificationScore(
                document_type=DocumentType.UNKNOWN,
                confidence=0.0,
                evidence=["No strong keyword signals detected"],
            )

        segment.document_type = best.document_type
        segment.classification_confidence = best.confidence
        segment.classification_evidence = best.evidence
        return segment

    @staticmethod
    def _collect_segment_text(
        segment: DocumentSegment,
        ocr_results: list[OCRPageResult],
    ) -> str:
        pages = {
            result.page_number: result.full_text
            for result in ocr_results
            if segment.page_start <= result.page_number <= segment.page_end
        }
        return "\n".join(pages[page_num] for page_num in sorted(pages))

    @staticmethod
    def _score_keywords(
        text: str,
        document_type: DocumentType,
        keywords: tuple[str, ...],
    ) -> ClassificationScore:
        evidence: list[str] = []
        hits = 0

        for keyword in keywords:
            if keyword in text:
                hits += 1
                evidence.append(f"Matched keyword: {keyword}")

        pattern_map = {
            DocumentType.INVOICE: r"\binv[\s#.-]*\d+",
            DocumentType.RECEIPT: r"\breceipt[\s#.-]*\d+",
            DocumentType.PURCHASE_ORDER: r"\bpo[\s#.-]*\d+",
        }
        pattern = pattern_map.get(document_type)
        if pattern and re.search(pattern, text, re.IGNORECASE):
            hits += 1
            evidence.append(f"Matched pattern: {pattern}")

        confidence = min(1.0, hits * 0.25) if hits else 0.0
        return ClassificationScore(document_type, confidence, evidence)
