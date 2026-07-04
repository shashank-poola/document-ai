from abc import ABC, abstractmethod

from app.schemas.ocr import OCRPageResult
from app.schemas.page import Page


class OCRProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier stored in OCR results."""

    @abstractmethod
    def process_pages(self, pages: list[Page]) -> list[OCRPageResult]:
        """Run OCR on a list of normalized pages."""
