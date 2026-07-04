from pydantic import BaseModel, Field

from app.schemas.enums import PageSource


class Page(BaseModel):
    page_number: int = Field(ge=1, description="1-based page index")
    image_path: str | None = None
    native_text: str | None = None
    source: PageSource = PageSource.NEEDS_OCR
    width: int | None = None
    height: int | None = None
    rotation: int = 0
