from pydantic import BaseModel, Field

from app.schemas.artifact_plan import ArtifactPlan
from app.schemas.document_spec import DocumentSpec
from app.schemas.generation_spec import GenerationSpec


class LLMMessage(BaseModel):
    role: str
    content: str


class LLMPlanningResponse(BaseModel):
    generation_spec: GenerationSpec = Field(default_factory=GenerationSpec)
    document_spec: DocumentSpec | None = None
    artifact_plan: ArtifactPlan = Field(default_factory=ArtifactPlan)
    warnings: list[str] = Field(default_factory=list)


class LLMPlanningResult(BaseModel):
    generation_spec: GenerationSpec
    document_spec: DocumentSpec | None = None
    artifact_plan: ArtifactPlan
    warnings: list[str] = Field(default_factory=list)
    raw_output: str | None = None
    skipped_reason: str | None = None
