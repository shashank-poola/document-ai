from pathlib import Path
from uuid import UUID

from docx import Document

from app.schemas.enums import PageSource
from app.schemas.page import Page
from app.utils.logging import get_logger

logger = get_logger(__name__)


class DocxPreprocessor:
    """Extract text and embedded images from DOCX files."""

    def process(self, job_id: UUID, source_path: Path, pages_dir: Path) -> list[Page]:
        document = Document(source_path)
        native_text = "\n".join(paragraph.text for paragraph in document.paragraphs).strip()

        pages: list[Page] = []
        image_index = 0

        for relationship in document.part.rels.values():
            if "image" not in relationship.reltype:
                continue

            image_index += 1
            image_bytes = relationship.target_part.blob
            image_path = pages_dir / f"page_{image_index:04d}.png"
            image_path.write_bytes(image_bytes)

            pages.append(
                Page(
                    page_number=image_index,
                    image_path=str(image_path),
                    native_text=native_text if image_index == 1 else None,
                    source=PageSource.MIXED if native_text else PageSource.NEEDS_OCR,
                )
            )

        if not pages and native_text:
            text_path = pages_dir / "page_0001.txt"
            text_path.write_text(native_text, encoding="utf-8")
            pages.append(
                Page(
                    page_number=1,
                    image_path=None,
                    native_text=native_text,
                    source=PageSource.TEXT_NATIVE,
                )
            )

        logger.info("docx_preprocessed", job_id=str(job_id), page_count=len(pages))
        return pages
