from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.schemas.artifact_plan import ArtifactPlan
from app.schemas.formats import ArtifactFormat


@dataclass(frozen=True)
class RenderedArtifact:
    file_name: str
    file_path: Path
    file_size: int


class BaseRenderer(Protocol):
    output_format: ArtifactFormat

    def render(self, artifact_id: str, plan: ArtifactPlan) -> RenderedArtifact:
        pass
