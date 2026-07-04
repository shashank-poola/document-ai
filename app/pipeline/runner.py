from datetime import datetime
from uuid import UUID

from app.classification import ClassificationService
from app.extraction import ExtractionService
from app.ocr import OCRService
from app.output import OutputService
from app.preprocessing import PreprocessingService
from app.schemas import JobRecord, JobStatus, PipelineOutput
from app.storage import get_storage
from app.utils.exceptions import PipelineStageError
from app.utils.logging import get_logger
from app.validation import ValidationService

logger = get_logger(__name__)


class PipelineRunner:
    """Orchestrates the document processing pipeline end-to-end.

    Phase 1: single-page vertical slice (image or single-page PDF).
    Phase 2: multi-page PDFs treated as one logical document (passthrough boundary).
    Phase 3+: multi-document boundary detection replaces passthrough.
    """

    def __init__(self) -> None:
        self._storage = get_storage()
        self._preprocessing = PreprocessingService()
        self._ocr = OCRService()
        self._classification = ClassificationService()
        self._extraction = ExtractionService()
        self._validation = ValidationService()
        self._output = OutputService()

    async def run(self, job_id: UUID) -> PipelineOutput:
        record = self._storage.load_job_record(job_id)
        logger.info("pipeline_started", job_id=str(job_id), filename=record.original_filename)

        try:
            record = self._update_status(record, JobStatus.PREPROCESSING)
            pages = self._preprocessing.run(job_id, record.file_format, record.original_filename)
            record.page_count = len(pages)

            record = self._update_status(record, JobStatus.OCR)
            ocr_results = self._ocr.run(job_id, pages)

            record = self._update_status(record, JobStatus.BOUNDARY_DETECTION)
            record = self._update_status(record, JobStatus.CLASSIFICATION)
            segments = self._classification.run(ocr_results)
            record.segment_count = len(segments)

            record = self._update_status(record, JobStatus.EXTRACTION)
            extractions = self._extraction.run(segments, ocr_results)

            record = self._update_status(record, JobStatus.VALIDATION)
            validations = self._validation.run(extractions)

            record = self._update_status(record, JobStatus.OUTPUT)
            job_dir = self._storage.ensure_job_dirs(job_id)
            segment_outputs = self._output.run(
                job_id,
                segments,
                extractions,
                validations,
                job_dir / "output",
            )

            needs_review = any(item.validation.needs_review for item in segment_outputs)
            final_status = JobStatus.NEEDS_REVIEW if needs_review else JobStatus.COMPLETED

            pipeline_output = PipelineOutput(
                job_id=job_id,
                status=final_status,
                original_filename=record.original_filename,
                page_count=record.page_count,
                segments=segment_outputs,
            )
            self._storage.save_pipeline_output(job_id, pipeline_output)

            record.status = final_status
            record.completed_at = datetime.utcnow()
            record.updated_at = datetime.utcnow()
            self._storage.save_job_record(record)

            logger.info(
                "pipeline_completed",
                job_id=str(job_id),
                status=final_status,
                pages=record.page_count,
                segments=record.segment_count,
            )
            return pipeline_output

        except PipelineStageError as exc:
            self._fail_job(record, exc.stage, str(exc))
            raise
        except Exception as exc:
            self._fail_job(record, record.status.value, str(exc))
            raise PipelineStageError("pipeline", str(exc)) from exc

    def _update_status(self, record: JobRecord, status: JobStatus) -> JobRecord:
        record.status = status
        record.updated_at = datetime.utcnow()
        self._storage.save_job_record(record)
        return record

    def _fail_job(self, record: JobRecord, stage: str, message: str) -> None:
        record.status = JobStatus.FAILED
        record.error_stage = stage
        record.error_message = message
        record.updated_at = datetime.utcnow()
        self._storage.save_job_record(record)
        logger.error("pipeline_failed", job_id=str(record.job_id), stage=stage, error=message)
