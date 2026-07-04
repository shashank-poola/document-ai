from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import FileFormat, JobStatus


class JobCreate(BaseModel):
    original_filename: str
    content_type: str | None = None
    file_size_bytes: int


class JobRecord(BaseModel):
    job_id: UUID
    status: JobStatus = JobStatus.PENDING
    original_filename: str
    content_type: str | None = None
    file_format: FileFormat | None = None
    file_size_bytes: int = 0
    error_stage: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    page_count: int = 0
    segment_count: int = 0


class JobEnqueuePayload(BaseModel):
    job_id: UUID


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    original_filename: str
    page_count: int = 0
    segment_count: int = 0
    error_stage: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
