from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID

from app.schemas import JobRecord, PipelineOutput
from app.schemas.ocr import OCRPageResult
from app.schemas.page import Page


class StorageBackend(ABC):
    @abstractmethod
    def ensure_job_dirs(self, job_id: UUID) -> Path:
        """Create and return the root directory for a job."""

    @abstractmethod
    def save_original(self, job_id: UUID, filename: str, content: bytes) -> Path:
        """Persist the uploaded source file."""

    @abstractmethod
    def save_job_record(self, record: JobRecord) -> None:
        """Persist job metadata."""

    @abstractmethod
    def load_job_record(self, job_id: UUID) -> JobRecord:
        """Load job metadata."""

    @abstractmethod
    def save_pages(self, job_id: UUID, pages: list[Page]) -> None:
        """Persist normalized page metadata."""

    @abstractmethod
    def load_pages(self, job_id: UUID) -> list[Page]:
        """Load normalized page metadata."""

    @abstractmethod
    def save_ocr_results(self, job_id: UUID, results: list[OCRPageResult]) -> None:
        """Persist OCR output per page."""

    @abstractmethod
    def load_ocr_results(self, job_id: UUID) -> list[OCRPageResult]:
        """Load OCR output per page."""

    @abstractmethod
    def save_pipeline_output(self, job_id: UUID, output: PipelineOutput) -> Path:
        """Persist final pipeline output."""

    @abstractmethod
    def load_pipeline_output(self, job_id: UUID) -> PipelineOutput:
        """Load final pipeline output."""

    @abstractmethod
    def job_exists(self, job_id: UUID) -> bool:
        """Return whether a job directory exists."""
