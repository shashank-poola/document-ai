class DocumentIntelligenceError(Exception):
    """Base exception for the document intelligence platform."""


class JobNotFoundError(DocumentIntelligenceError):
    """Raised when a processing job cannot be located."""


class UnsupportedFileTypeError(DocumentIntelligenceError):
    """Raised when an uploaded file format is not supported."""


class PipelineStageError(DocumentIntelligenceError):
    """Raised when a pipeline stage fails irrecoverably."""

    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        super().__init__(f"[{stage}] {message}")


class ValidationError(DocumentIntelligenceError):
    """Raised when extracted data fails validation rules."""
