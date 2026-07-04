import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from paddleocr import PaddleOCR

from app.config import get_settings
from app.ocr.base import OCRProvider
from app.schemas.enums import PageSource
from app.schemas.ocr import OCRPageResult, TextBlock
from app.schemas.page import Page
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Skip slow model-host connectivity checks on worker startup.
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")


@lru_cache
def _create_paddle_engine(lang: str, device: str) -> PaddleOCR:
    return PaddleOCR(
        lang=lang,
        device=device,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=True,
    )


class PaddleOCRProvider(OCRProvider):
    """PaddleOCR-backed text extraction with layout and confidence metadata."""

    def __init__(self) -> None:
        settings = get_settings()
        device = "gpu" if settings.ocr_use_gpu else "cpu"
        self._engine = _create_paddle_engine(settings.ocr_lang, device)

    @property
    def name(self) -> str:
        return "paddleocr"

    def process_pages(self, pages: list[Page]) -> list[OCRPageResult]:
        results: list[OCRPageResult] = []

        for page in pages:
            if page.source == PageSource.TEXT_NATIVE and page.native_text:
                results.append(self._from_native_text(page))
                continue

            if not page.image_path:
                results.append(
                    OCRPageResult(
                        page_number=page.page_number,
                        full_text=page.native_text or "",
                        average_confidence=1.0 if page.native_text else 0.0,
                        provider=self.name,
                    )
                )
                continue

            results.append(self._ocr_image(page))

        logger.info("ocr_completed", page_count=len(results), provider=self.name)
        return results

    def _from_native_text(self, page: Page) -> OCRPageResult:
        text = page.native_text or ""
        return OCRPageResult(
            page_number=page.page_number,
            full_text=text,
            blocks=[TextBlock(text=text, confidence=1.0)],
            average_confidence=1.0,
            provider=self.name,
        )

    def _ocr_image(self, page: Page) -> OCRPageResult:
        image_path = Path(page.image_path)
        predictions = list(self._engine.predict(str(image_path)))
        blocks = self._parse_predictions(predictions)

        full_text = "\n".join(block.text for block in blocks)
        if page.native_text:
            full_text = f"{page.native_text}\n{full_text}".strip()

        avg_confidence = (
            round(sum(block.confidence for block in blocks) / len(blocks), 4) if blocks else 0.0
        )

        return OCRPageResult(
            page_number=page.page_number,
            full_text=full_text,
            blocks=blocks,
            average_confidence=avg_confidence,
            provider=self.name,
        )

    @staticmethod
    def _parse_predictions(predictions: list[Any]) -> list[TextBlock]:
        blocks: list[TextBlock] = []

        for prediction in predictions:
            payload = prediction if isinstance(prediction, dict) else None
            if payload is None:
                payload = getattr(prediction, "json", None)
            if payload is None and hasattr(prediction, "to_dict"):
                payload = prediction.to_dict()
            if not isinstance(payload, dict):
                continue

            texts = payload.get("rec_texts") or payload.get("texts") or []
            scores = payload.get("rec_scores") or payload.get("scores") or []
            boxes = (
                payload.get("rec_boxes")
                or payload.get("dt_polys")
                or payload.get("boxes")
                or []
            )

            for index, text in enumerate(texts):
                if not text:
                    continue
                confidence = float(scores[index]) if index < len(scores) else 0.0
                bbox = PaddleOCRProvider._flatten_bbox(boxes[index]) if index < len(boxes) else []
                blocks.append(TextBlock(text=str(text), confidence=round(confidence, 4), bbox=bbox))

        if blocks:
            return blocks

        # Fallback for legacy list-style OCR output.
        for prediction in predictions:
            if not isinstance(prediction, list):
                continue
            for line in prediction:
                if not line or len(line) < 2:
                    continue
                bbox_points, text_data = line[0], line[1]
                if isinstance(text_data, tuple):
                    text, confidence = text_data
                else:
                    text, confidence = str(text_data), 0.0
                blocks.append(
                    TextBlock(
                        text=str(text),
                        confidence=round(float(confidence), 4),
                        bbox=PaddleOCRProvider._flatten_bbox(bbox_points),
                    )
                )

        return blocks

    @staticmethod
    def _flatten_bbox(bbox_points: Any) -> list[float]:
        if bbox_points is None:
            return []
        if isinstance(bbox_points, dict):
            return [float(value) for value in bbox_points.get("coordinate", [])]
        if len(bbox_points) == 4 and all(isinstance(value, (int, float)) for value in bbox_points):
            return [float(value) for value in bbox_points]
        flat: list[float] = []
        for point in bbox_points:
            if isinstance(point, (list, tuple)):
                flat.extend(float(coord) for coord in point)
        return flat
