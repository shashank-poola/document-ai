from functools import lru_cache
from uuid import UUID

from app.ocr.base import OCRProvider
from app.ocr.paddle import PaddleOCRProvider
from app.schemas.ocr import OCRPageResult
from app.schemas.page import Page
from app.storage import get_storage
from app.utils.exceptions import PipelineStageError


class OCRService:
    def __init__(self, provider: OCRProvider | None = None) -> None:
        self._provider = provider or get_ocr_provider()
        self._storage = get_storage()

    def run(self, job_id: UUID, pages: list[Page]) -> list[OCRPageResult]:
        try:
            results = self._provider.process_pages(pages)
        except Exception as exc:
            raise PipelineStageError("ocr", str(exc)) from exc

        self._storage.save_ocr_results(job_id, results)
        return results


@lru_cache
def get_ocr_provider() -> OCRProvider:
    return PaddleOCRProvider()
