from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.formats import (
    DEFAULT_OUTPUT_FORMAT,
    ArtifactFormat,
    is_render_supported,
    supported_render_format_values,
)


OutputFormat = ArtifactFormat


class ArtifactStatus(StrEnum):
    queued = "queued"
    processing = "processing"
    ready = "ready"
    failed = "failed"
    canceled = "canceled"


class DocumentCreateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=50_000)
    output_format: OutputFormat | None = None
    overrides: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @field_validator("output_format")
    @classmethod
    def validate_supported_output_format(cls, value: OutputFormat | None) -> OutputFormat | None:
        if value is None:
            return value
        if is_render_supported(value):
            return value

        supported_formats = ", ".join(supported_render_format_values())
        raise ValueError(
            f"Output format '{value}' is known but not supported yet. "
            f"Supported formats: {supported_formats}."
        )

    @property
    def requested_output_format(self) -> OutputFormat:
        return self.output_format or DEFAULT_OUTPUT_FORMAT


class DocumentCreateResponse(BaseModel):
    document_id: str
    request_id: str
    job_id: str | None = None
    status: ArtifactStatus
    current_stage: str | None = None
    output_format: OutputFormat
    file_name: str | None = None
    status_url: str | None = None
    download_url: str | None = None
    error_message: str | None = None
    warnings: list[str] = Field(default_factory=list)


class DocumentInfoResponse(BaseModel):
    document_id: str
    request_id: str
    job_id: str | None = None
    status: ArtifactStatus
    current_stage: str | None = None
    output_format: OutputFormat
    file_name: str | None = None
    status_url: str | None = None
    download_url: str | None = None
    error_message: str | None = None
    warnings: list[str] = Field(default_factory=list)
