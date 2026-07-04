from functools import lru_cache
from pathlib import Path

from paddleocr import PaddleOCR

from app.config import get_settings
from app.ocr.base import OCRProvider
from app.schemas.enums import PageSource
from app.schemas.ocr import OCRPageResult, TextBlock
from app.schemas.page import Page
from app.utils.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def _create_paddle_engine(lang: str, use_gpu: bool) -> PaddleOCR:
    return PaddleOCR(
        use_angle_cls=True,
        lang=lang,
        use_gpu=use_gpu,
        show_log=False,
    )


class PaddleOCRProvider(OCRProvider):
    """PaddleOCR-backed text extraction with layout and confidence metadata."""

    def __init__(self) -> None:
        settings = get_settings()
        self._engine = _create_paddle_engine(settings.ocr_lang, settings.ocr_use_gpu)

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
        raw = self._engine.ocr(str(image_path), cls=True)

        blocks: list[TextBlock] = []
        if raw and raw[0]:
            for line in raw[0]:
                bbox_points, (text, confidence) = line
                flat_bbox = [float(coord) for point in bbox_points for coord in point]
                blocks.append(
                    TextBlock(
                        text=text,
                        confidence=round(confidence, 4),
                        bbox=flat_bbox,
                    )
                )

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
