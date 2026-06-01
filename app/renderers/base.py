from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from app.schemas.artifact_plan import ArtifactPlan
from app.schemas.document_spec import DocumentSpec
from app.schemas.formats import ArtifactFormat


@dataclass(frozen=True)
class RenderedArtifact:
    file_name: str
    file_path: Path
    file_size: int
    warnings: list[str] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)


class BaseRenderer(Protocol):
    output_format: ArtifactFormat

    def render(self, artifact_id: str, plan: ArtifactPlan | DocumentSpec) -> RenderedArtifact:
        pass
