from pathlib import Path

from app.schemas.enums import FileFormat


def detect_file_format(filename: str) -> FileFormat:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return FileFormat.PDF
    if suffix in {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".webp"}:
        return FileFormat.IMAGE
    if suffix == ".docx":
        return FileFormat.DOCX
    msg = f"Unsupported file extension: {suffix}"
    raise ValueError(msg)
