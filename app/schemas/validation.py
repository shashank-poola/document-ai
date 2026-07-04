from pydantic import BaseModel, Field

from app.schemas.enums import ValidationStatus


class FieldValidation(BaseModel):
  field_name: str
  value: str | None = None
  confidence: float = Field(default=0.0, ge=0.0, le=1.0)
  status: ValidationStatus = ValidationStatus.PASS
  messages: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
  segment_id: str
  overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
  needs_review: bool = False
  field_validations: list[FieldValidation] = Field(default_factory=list)
