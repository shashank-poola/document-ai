from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "document-intelligence"
    app_env: str = "development"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    storage_root: Path = Path("./data")
    max_upload_size_mb: int = 50

    redis_url: str = "redis://localhost:6379/0"
    queue_name: str = "document-processing"
    job_timeout_seconds: int = 600
    job_max_retries: int = 3

    ocr_lang: str = "en"
    ocr_use_gpu: bool = False
    ocr_dpi: int = 200

    review_confidence_threshold: float = 0.75

    allowed_extensions: frozenset[str] = Field(
        default=frozenset({".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".webp", ".docx"}),
        exclude=True,
    )

    @field_validator("storage_root", mode="before")
    @classmethod
    def resolve_storage_root(cls, value: str | Path) -> Path:
        return Path(value).resolve()

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def jobs_dir(self) -> Path:
        return self.storage_root / "jobs"

    @property
    def samples_dir(self) -> Path:
        return self.storage_root / "samples"

    @property
    def outputs_dir(self) -> Path:
        return self.storage_root / "outputs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
