import json
from pathlib import Path
from uuid import UUID

from app.schemas.extraction import ExtractionResult
from app.schemas.output import SegmentOutput
from app.schemas.segment import DocumentSegment
from app.schemas.validation import ValidationResult


class MarkdownGenerator:
    def generate(
        self,
        segment: DocumentSegment,
        extraction: ExtractionResult,
        validation: ValidationResult,
    ) -> str:
        title = segment.document_type.value.replace("_", " ").title()
        lines = [
            f"# {title}",
            "",
            f"**Segment:** {segment.segment_id} (pages {segment.page_start}-{segment.page_end})",
            f"**Confidence:** {validation.overall_confidence:.0%}",
            "",
        ]

        if validation.needs_review:
            lines.extend(["> ⚠️ Flagged for human review", ""])

        field_map = extraction.fields.model_dump()
        for field_name, value in field_map.items():
            if value:
                label = field_name.replace("_", " ").title()
                lines.extend([f"**{label}:**", str(value), ""])

        warnings = [
            item
            for item in validation.field_validations
            if item.messages and item.status.value != "pass"
        ]
        if warnings:
            lines.extend(["## Validation Notes", ""])
            for item in warnings:
                for message in item.messages:
                    lines.append(f"- {message}")
            lines.append("")

        return "\n".join(lines).strip() + "\n"


class JsonGenerator:
    def generate(
        self,
        segment: DocumentSegment,
        extraction: ExtractionResult,
        validation: ValidationResult,
    ) -> dict:
        return {
            "schema_version": "1.0",
            "segment": segment.model_dump(),
            "extraction": extraction.model_dump(),
            "validation": validation.model_dump(),
        }


class OutputService:
    def __init__(self) -> None:
        self._markdown = MarkdownGenerator()
        self._json = JsonGenerator()

    def run(
        self,
        job_id: UUID,
        segments: list[DocumentSegment],
        extractions: list[ExtractionResult],
        validations: list[ValidationResult],
        output_dir: Path,
    ) -> list[SegmentOutput]:
        extraction_by_segment = {item.segment_id: item for item in extractions}
        validation_by_segment = {item.segment_id: item for item in validations}

        segment_outputs: list[SegmentOutput] = []
        output_dir.mkdir(parents=True, exist_ok=True)

        for segment in segments:
            extraction = extraction_by_segment[segment.segment_id]
            validation = validation_by_segment[segment.segment_id]

            markdown = self._markdown.generate(segment, extraction, validation)
            json_data = self._json.generate(segment, extraction, validation)

            segment_dir = output_dir / segment.segment_id
            segment_dir.mkdir(parents=True, exist_ok=True)

            markdown_path = segment_dir / "summary.md"
            json_path = segment_dir / "structured.json"

            markdown_path.write_text(markdown, encoding="utf-8")
            json_path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")

            segment_outputs.append(
                SegmentOutput(
                    segment=segment,
                    extraction=extraction,
                    validation=validation,
                    markdown=markdown,
                    json_path=str(json_path),
                    markdown_path=str(markdown_path),
                )
            )

        return segment_outputs
