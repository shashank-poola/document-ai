import json
import shutil
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.schemas import JobRecord, PipelineOutput
from app.schemas.ocr import OCRPageResult
from app.schemas.page import Page
from app.storage.base import StorageBackend
from app.utils.exceptions import JobNotFoundError


class LocalStorageBackend(StorageBackend):
    """Filesystem-backed storage for development and single-node deployments."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)
        (self._root / "jobs").mkdir(exist_ok=True)

    def _job_dir(self, job_id: UUID) -> Path:
        return self._root / "jobs" / str(job_id)

    def ensure_job_dirs(self, job_id: UUID) -> Path:
        job_dir = self._job_dir(job_id)
        for subdir in ("original", "pages", "ocr", "segments", "output"):
            (job_dir / subdir).mkdir(parents=True, exist_ok=True)
        return job_dir

    def save_original(self, job_id: UUID, filename: str, content: bytes) -> Path:
        job_dir = self.ensure_job_dirs(job_id)
        destination = job_dir / "original" / filename
        destination.write_bytes(content)
        return destination

    def _metadata_path(self, job_id: UUID) -> Path:
        return self._job_dir(job_id) / "metadata.json"

    def save_job_record(self, record: JobRecord) -> None:
        self.ensure_job_dirs(record.job_id)
        record.updated_at = datetime.utcnow()
        self._metadata_path(record.job_id).write_text(
            record.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def load_job_record(self, job_id: UUID) -> JobRecord:
        path = self._metadata_path(job_id)
        if not path.exists():
            raise JobNotFoundError(f"Job not found: {job_id}")
        return JobRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def save_pages(self, job_id: UUID, pages: list[Page]) -> None:
        pages_dir = self.ensure_job_dirs(job_id) / "pages"
        index_path = pages_dir / "index.json"
        index_path.write_text(
            json.dumps([page.model_dump() for page in pages], indent=2),
            encoding="utf-8",
        )

    def load_pages(self, job_id: UUID) -> list[Page]:
        index_path = self._job_dir(job_id) / "pages" / "index.json"
        if not index_path.exists():
            raise JobNotFoundError(f"Pages not found for job: {job_id}")
        data = json.loads(index_path.read_text(encoding="utf-8"))
        return [Page.model_validate(item) for item in data]

    def save_ocr_results(self, job_id: UUID, results: list[OCRPageResult]) -> None:
        ocr_dir = self.ensure_job_dirs(job_id) / "ocr"
        for result in results:
            page_path = ocr_dir / f"page_{result.page_number:04d}.json"
            page_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

        combined = ocr_dir / "combined.json"
        combined.write_text(
            json.dumps([item.model_dump() for item in results], indent=2),
            encoding="utf-8",
        )

    def load_ocr_results(self, job_id: UUID) -> list[OCRPageResult]:
        combined = self._job_dir(job_id) / "ocr" / "combined.json"
        if not combined.exists():
            raise JobNotFoundError(f"OCR results not found for job: {job_id}")
        data = json.loads(combined.read_text(encoding="utf-8"))
        return [OCRPageResult.model_validate(item) for item in data]

    def save_pipeline_output(self, job_id: UUID, output: PipelineOutput) -> Path:
        output_dir = self.ensure_job_dirs(job_id) / "output"
        path = output_dir / "pipeline_output.json"
        path.write_text(output.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load_pipeline_output(self, job_id: UUID) -> PipelineOutput:
        path = self._job_dir(job_id) / "output" / "pipeline_output.json"
        if not path.exists():
            raise JobNotFoundError(f"Pipeline output not found for job: {job_id}")
        return PipelineOutput.model_validate_json(path.read_text(encoding="utf-8"))

    def job_exists(self, job_id: UUID) -> bool:
        return self._metadata_path(job_id).exists()

    def delete_job(self, job_id: UUID) -> None:
        job_dir = self._job_dir(job_id)
        if job_dir.exists():
            shutil.rmtree(job_dir)
