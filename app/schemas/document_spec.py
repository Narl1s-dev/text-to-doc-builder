from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.artifact_plan import ArtifactBlock, ArtifactPlan
from app.schemas.formats import DEFAULT_OUTPUT_FORMAT, ArtifactFormat
from app.schemas.generation_spec import FormattingSpec, GenerationSpec


class DocumentSpec(BaseModel):
    schema_version: Literal["document_spec.v1"] = "document_spec.v1"
    output_format: ArtifactFormat = DEFAULT_OUTPUT_FORMAT
    document_type: str = "general_document"
    title: str = "Документ"
    language: str = "ru"
    audience: str = "general"
    tone: str = "neutral"
    style: str = "business"
    formatting: FormattingSpec = Field(default_factory=FormattingSpec)
    content_markdown: str = Field(..., min_length=1)
    source_facts: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")

    @field_validator("title", "content_markdown")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Text must not be empty.")
        return normalized


def document_spec_from_plan(
    generation_spec: GenerationSpec,
    artifact_plan: ArtifactPlan,
) -> DocumentSpec:
    metadata = dict(artifact_plan.metadata)
    metadata.setdefault("artifact_type", artifact_plan.artifact_type)

    content_markdown = metadata.pop("content_markdown", None)
    if not isinstance(content_markdown, str) or not content_markdown.strip():
        content_markdown = artifact_blocks_to_markdown(
            artifact_plan.blocks,
            fallback_title=artifact_plan.title or generation_spec.title,
        )

    return DocumentSpec(
        output_format=artifact_plan.output_format or generation_spec.output_format,
        document_type=generation_spec.document_type,
        title=artifact_plan.title or generation_spec.title,
        language=generation_spec.language,
        audience=generation_spec.audience,
        tone=generation_spec.tone,
        style=generation_spec.style,
        formatting=artifact_plan.formatting or generation_spec.formatting,
        content_markdown=content_markdown,
        source_facts=generation_spec.source_facts,
        metadata=metadata,
    )


def artifact_blocks_to_markdown(blocks: list[ArtifactBlock], *, fallback_title: str) -> str:
    if not blocks:
        return f"# {fallback_title.strip() or 'Документ'}"

    parts: list[str] = []
    for block in blocks:
        match block.type:
            case "heading":
                level = max(1, min(block.level or 1, 6))
                parts.append(f"{'#' * level} {block.text or fallback_title}")
            case "paragraph":
                if block.text:
                    parts.append(block.text)
            case "bullet_list":
                parts.extend(f"- {item}" for item in block.items if item)
            case "numbered_list":
                parts.extend(f"{index}. {item}" for index, item in enumerate(block.items, start=1) if item)
            case "table":
                table_markdown = _table_to_markdown(block.rows)
                if table_markdown:
                    parts.append(table_markdown)

    content = "\n\n".join(part for part in parts if part.strip()).strip()
    return content or f"# {fallback_title.strip() or 'Документ'}"


def _table_to_markdown(rows: list[list[str]]) -> str | None:
    if not rows:
        return None

    column_count = max(len(row) for row in rows)
    normalized_rows = [
        [row[index] if index < len(row) else "" for index in range(column_count)]
        for row in rows
    ]
    header = normalized_rows[0]
    separator = ["---"] * column_count
    body = normalized_rows[1:]
    markdown_rows = [header, separator, *body]
    return "\n".join("| " + " | ".join(cell.strip() for cell in row) + " |" for row in markdown_rows)
