from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.formats import DEFAULT_OUTPUT_FORMAT, ArtifactFormat


class LengthSpec(BaseModel):
    mode: str = "medium"
    max_pages: int | None = None

    model_config = ConfigDict(extra="ignore")


class MarginSpec(BaseModel):
    top_cm: float = 2
    right_cm: float = 1.5
    bottom_cm: float = 2
    left_cm: float = 3

    model_config = ConfigDict(extra="ignore")


class FormattingSpec(BaseModel):
    page_size: str = "A4"
    orientation: str = "portrait"
    font_family: str = "Times New Roman"
    font_size: int = 12
    line_spacing: float = 1.15
    paragraph_spacing_after: int = 6
    margins: MarginSpec = Field(default_factory=MarginSpec)

    model_config = ConfigDict(extra="ignore")


class StructureSpec(BaseModel):
    include_title: bool = True
    include_summary: bool = False
    sections: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class GenerationSpec(BaseModel):
    output_format: ArtifactFormat = DEFAULT_OUTPUT_FORMAT
    document_type: str = "general_document"
    title: str = "Документ"
    language: str = "ru"
    audience: str = "general"
    tone: str = "neutral"
    style: str = "business"
    length: LengthSpec = Field(default_factory=LengthSpec)
    source_facts: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    formatting: FormattingSpec = Field(default_factory=FormattingSpec)
    structure: StructureSpec = Field(default_factory=StructureSpec)

    model_config = ConfigDict(extra="ignore")
