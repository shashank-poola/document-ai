from app.boundary_detection import PassthroughBoundaryDetector
from app.classification.heuristics import HeuristicClassifier
from app.schemas.ocr import OCRPageResult
from app.schemas.segment import DocumentSegment


class ClassificationService:
    def __init__(self) -> None:
        self._boundary_detector = PassthroughBoundaryDetector()
        self._classifier = HeuristicClassifier()

    def run(self, ocr_results: list[OCRPageResult]) -> list[DocumentSegment]:
        segments = self._boundary_detector.detect(ocr_results)
        return [self._classifier.classify_segment(segment, ocr_results) for segment in segments]
