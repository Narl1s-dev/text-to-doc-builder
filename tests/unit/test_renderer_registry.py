import pytest

from app.renderers.base import RenderedArtifact
from app.renderers.registry import RendererRegistry, UnsupportedRendererError
from app.schemas.artifact_plan import ArtifactPlan
from app.schemas.formats import ArtifactFormat


class FakeRenderer:
    def __init__(self, output_format: ArtifactFormat) -> None:
        self.output_format = output_format

    def render(self, artifact_id: str, plan: ArtifactPlan) -> RenderedArtifact:
        raise NotImplementedError


def test_renderer_registry_selects_registered_renderer_by_format() -> None:
    docx_renderer = FakeRenderer(ArtifactFormat.docx)
    pdf_renderer = FakeRenderer(ArtifactFormat.pdf)
    registry = RendererRegistry([docx_renderer, pdf_renderer])

    assert registry.get(ArtifactFormat.docx) is docx_renderer
    assert registry.get("pdf") is pdf_renderer
    assert registry.supported_formats() == (ArtifactFormat.docx, ArtifactFormat.pdf)


def test_renderer_registry_rejects_known_format_without_adapter() -> None:
    registry = RendererRegistry([FakeRenderer(ArtifactFormat.docx)])

    with pytest.raises(UnsupportedRendererError, match="Renderer for 'pptx' is not configured"):
        registry.get(ArtifactFormat.pptx)


def test_renderer_registry_rejects_unknown_format() -> None:
    registry = RendererRegistry([FakeRenderer(ArtifactFormat.docx)])

    with pytest.raises(UnsupportedRendererError, match="Unknown artifact format 'zip'"):
        registry.get("zip")
