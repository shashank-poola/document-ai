from pathlib import Path
from uuid import UUID

from PIL import Image, ImageOps

from app.schemas.enums import PageSource
from app.schemas.page import Page
from app.utils.logging import get_logger

logger = get_logger(__name__)

SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".webp"}


class ImagePreprocessor:
    """Normalize image files into a consistent PNG representation."""

    def process(self, job_id: UUID, source_path: Path, pages_dir: Path) -> list[Page]:
        suffix = source_path.suffix.lower()
        if suffix not in SUPPORTED_IMAGE_SUFFIXES:
            msg = f"Unsupported image format: {suffix}"
            raise ValueError(msg)

        with Image.open(source_path) as image:
            normalized = ImageOps.exif_transpose(image).convert("RGB")
            image_path = pages_dir / "page_0001.png"
            normalized.save(image_path, format="PNG")

            page = Page(
                page_number=1,
                image_path=str(image_path),
                native_text=None,
                source=PageSource.NEEDS_OCR,
                width=normalized.width,
                height=normalized.height,
            )

        logger.info("image_preprocessed", job_id=str(job_id))
        return [page]
