from pathlib import Path
from uuid import UUID

from app.preprocessing.detector import detect_file_format
from app.preprocessing.docx import DocxPreprocessor
from app.preprocessing.image import ImagePreprocessor
from app.preprocessing.pdf import PDFPreprocessor
from app.schemas.enums import FileFormat
from app.schemas.page import Page
from app.storage import get_storage
from app.utils.exceptions import PipelineStageError


class PreprocessingService:
    def __init__(self) -> None:
        self._pdf = PDFPreprocessor()
        self._image = ImagePreprocessor()
        self._docx = DocxPreprocessor()
        self._storage = get_storage()

    def run(self, job_id: UUID, file_format: FileFormat, original_filename: str) -> list[Page]:
        job_dir = self._storage.ensure_job_dirs(job_id)
        source_path = job_dir / "original" / original_filename
        pages_dir = job_dir / "pages"

        if not source_path.exists():
            raise PipelineStageError("preprocessing", f"Source file missing: {source_path}")

        try:
            pages = self._dispatch(file_format, job_id, source_path, pages_dir)
        except Exception as exc:
            raise PipelineStageError("preprocessing", str(exc)) from exc

        self._storage.save_pages(job_id, pages)
        return pages

    def _dispatch(
        self,
        file_format: FileFormat,
        job_id: UUID,
        source_path: Path,
        pages_dir: Path,
    ) -> list[Page]:
        if file_format == FileFormat.PDF:
            return self._pdf.process(job_id, source_path, pages_dir)
        if file_format == FileFormat.IMAGE:
            return self._image.process(job_id, source_path, pages_dir)
        if file_format == FileFormat.DOCX:
            return self._docx.process(job_id, source_path, pages_dir)

        raise PipelineStageError("preprocessing", f"Unsupported format: {file_format}")

    @staticmethod
    def resolve_format(filename: str) -> FileFormat:
        return detect_file_format(filename)
