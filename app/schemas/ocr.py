from pydantic import BaseModel, Field


class TextBlock(BaseModel):
  text: str
  confidence: float = Field(ge=0.0, le=1.0)
  bbox: list[float] = Field(default_factory=list, description="[x1, y1, x2, y2]")


class OCRPageResult(BaseModel):
  page_number: int = Field(ge=1)
  full_text: str = ""
  blocks: list[TextBlock] = Field(default_factory=list)
  average_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
  provider: str = "paddleocr"
