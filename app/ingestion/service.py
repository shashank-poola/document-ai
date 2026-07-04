from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status

from app.config import get_settings
from app.preprocessing import PreprocessingService
from app.queue import enqueue_document_job
from app.schemas import JobRecord, JobStatus, JobStatusResponse
from app.schemas.enums import FileFormat
from app.schemas.output import PipelineOutput
from app.storage import get_storage
from app.utils.exceptions import JobNotFoundError, UnsupportedFileTypeError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class IngestionService:
    def __init__(self) -> None:
        self._storage = get_storage()
        self._preprocessing = PreprocessingService()

    async def create_job(self, upload: UploadFile) -> JobRecord:
        filename = upload.filename or "upload"
        suffix = Path(filename).suffix.lower()

        cfg = get_settings()
        if suffix not in cfg.allowed_extensions:
            raise UnsupportedFileTypeError(f"Unsupported file type: {suffix}")

        content = await upload.read()
        if len(content) > cfg.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {cfg.max_upload_size_mb} MB",
            )

        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty",
            )

        job_id = uuid4()
        file_format = self._resolve_format(filename)

        record = JobRecord(
            job_id=job_id,
            status=JobStatus.PENDING,
            original_filename=filename,
            content_type=upload.content_type,
            file_format=file_format,
            file_size_bytes=len(content),
        )

        self._storage.ensure_job_dirs(job_id)
        self._storage.save_original(job_id, filename, content)
        self._storage.save_job_record(record)

        logger.info("job_created", job_id=str(job_id), filename=filename)
        return record

    async def submit_job(self, record: JobRecord) -> JobRecord:
        await enqueue_document_job(record.job_id)
        record.status = JobStatus.QUEUED
        record.updated_at = datetime.utcnow()
        self._storage.save_job_record(record)
        return record

    def get_status(self, job_id: UUID) -> JobStatusResponse:
        try:
            record = self._storage.load_job_record(job_id)
        except JobNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

        return JobStatusResponse(
            job_id=record.job_id,
            status=record.status,
            original_filename=record.original_filename,
            page_count=record.page_count,
            segment_count=record.segment_count,
            error_stage=record.error_stage,
            error_message=record.error_message,
            created_at=record.created_at,
            updated_at=record.updated_at,
            completed_at=record.completed_at,
        )

    def get_result(self, job_id: UUID) -> PipelineOutput:
        try:
            return self._storage.load_pipeline_output(job_id)
        except JobNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @staticmethod
    def _resolve_format(filename: str) -> FileFormat:
        return PreprocessingService.resolve_format(filename)
