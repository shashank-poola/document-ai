from pydantic import BaseModel, Field

from app.schemas.enums import DocumentType


class DocumentSegment(BaseModel):
  segment_id: str
  page_start: int = Field(ge=1)
  page_end: int = Field(ge=1)
  boundary_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
  document_type: DocumentType = DocumentType.UNKNOWN
  classification_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
  classification_evidence: list[str] = Field(default_factory=list)
