from pathlib import Path
from uuid import UUID

import fitz

from app.config import get_settings
from app.schemas.enums import PageSource
from app.schemas.page import Page
from app.utils.logging import get_logger

logger = get_logger(__name__)


class PDFPreprocessor:
    """Split PDF files into normalized page images and extract native text when available."""

    def __init__(self, dpi: int | None = None) -> None:
        settings = get_settings()
        self._dpi = dpi or settings.ocr_dpi
        self._zoom = self._dpi / 72.0

    def process(self, job_id: UUID, source_path: Path, pages_dir: Path) -> list[Page]:
        pages: list[Page] = []
        matrix = fitz.Matrix(self._zoom, self._zoom)

        with fitz.open(source_path) as document:
            for index in range(document.page_count):
                page_number = index + 1
                pdf_page = document[index]
                native_text = pdf_page.get_text("text").strip()

                pixmap = pdf_page.get_pixmap(matrix=matrix, alpha=False)
                image_path = pages_dir / f"page_{page_number:04d}.png"
                pixmap.save(str(image_path))

                source = self._resolve_source(native_text)
                pages.append(
                    Page(
                        page_number=page_number,
                        image_path=str(image_path),
                        native_text=native_text or None,
                        source=source,
                        width=pixmap.width,
                        height=pixmap.height,
                    )
                )

        logger.info("pdf_preprocessed", job_id=str(job_id), page_count=len(pages))
        return pages

    @staticmethod
    def _resolve_source(native_text: str) -> PageSource:
        if not native_text:
            return PageSource.NEEDS_OCR
        if len(native_text) > 100:
            return PageSource.TEXT_NATIVE
        return PageSource.MIXED
