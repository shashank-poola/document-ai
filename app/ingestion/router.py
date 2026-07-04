# ruff: noqa: B008

from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.ingestion.service import IngestionService
from app.schemas import JobStatusResponse
from app.schemas.enums import JobStatus
from app.schemas.output import PipelineOutput

router = APIRouter(prefix="/api/v1", tags=["documents"])
_service = IngestionService()


@router.post("/documents/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(file: UploadFile = File(...)) -> JobStatusResponse:
    """Accept a document, store it, and enqueue it for asynchronous processing."""
    record = await _service.create_job(file)
    record = await _service.submit_job(record)
    return _service.get_status(record.job_id)


@router.get("/documents/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: UUID) -> JobStatusResponse:
    """Poll processing status for an uploaded document."""
    return _service.get_status(job_id)


@router.get("/documents/{job_id}/result", response_model=PipelineOutput)
async def get_job_result(job_id: UUID) -> PipelineOutput:
    """Retrieve structured extraction results for a completed job."""
    status_response = _service.get_status(job_id)
    if status_response.status not in {JobStatus.COMPLETED, JobStatus.NEEDS_REVIEW}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is not ready. Current status: {status_response.status}",
        )
    return _service.get_result(job_id)
