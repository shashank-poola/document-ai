from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import JobStatus
from app.schemas.extraction import ExtractionResult
from app.schemas.segment import DocumentSegment
from app.schemas.validation import ValidationResult


class SegmentOutput(BaseModel):
  segment: DocumentSegment
  extraction: ExtractionResult
  validation: ValidationResult
  markdown: str
  json_path: str
  markdown_path: str


class PipelineOutput(BaseModel):
  job_id: UUID
  status: JobStatus
  original_filename: str
  page_count: int
  segments: list[SegmentOutput] = Field(default_factory=list)
  completed_at: datetime = Field(default_factory=datetime.utcnow)
  schema_version: str = "1.0"
