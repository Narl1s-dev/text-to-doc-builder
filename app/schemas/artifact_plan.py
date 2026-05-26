from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.formats import DEFAULT_OUTPUT_FORMAT, ArtifactFormat
from app.schemas.generation_spec import FormattingSpec


BlockType = Literal["heading", "paragraph", "bullet_list", "numbered_list", "table"]


class ArtifactBlock(BaseModel):
    type: BlockType
    text: str | None = None
    level: int | None = Field(default=None, ge=1, le=6)
    items: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ArtifactPlan(BaseModel):
    artifact_type: str = "document"
    output_format: ArtifactFormat = DEFAULT_OUTPUT_FORMAT
    title: str = "Документ"
    blocks: list[ArtifactBlock] = Field(default_factory=list)
    formatting: FormattingSpec = Field(default_factory=FormattingSpec)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")
