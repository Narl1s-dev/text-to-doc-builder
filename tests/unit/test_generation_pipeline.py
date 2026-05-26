from pathlib import Path

from app.llm.openrouter_client import OpenRouterError
from app.llm.schemas import LLMPlanningResult
from app.renderers.base import RenderedArtifact
from app.schemas.artifact_plan import ArtifactBlock, ArtifactPlan
from app.schemas.document import DocumentCreateRequest
from app.schemas.formats import ArtifactFormat
from app.schemas.generation_spec import GenerationSpec
from app.services.generation_pipeline import GenerationPipeline, PipelineFailure, PipelineSuccess


class SuccessfulPlanner:
    def plan(self, payload: DocumentCreateRequest) -> LLMPlanningResult:
        return LLMPlanningResult(
            generation_spec=GenerationSpec(title="План встречи"),
            artifact_plan=ArtifactPlan(
                title="План встречи",
                blocks=[
                    ArtifactBlock(type="heading", level=1, text="План встречи"),
                    ArtifactBlock(type="paragraph", text=payload.prompt),
                ],
            ),
            warnings=[],
            raw_output='{"ok": true}',
        )


class FailingPlanner:
    def plan(self, payload: DocumentCreateRequest) -> LLMPlanningResult:
        raise OpenRouterError("OpenRouter unavailable")


class PptxPlanner:
    def plan(self, payload: DocumentCreateRequest) -> LLMPlanningResult:
        return LLMPlanningResult(
            generation_spec=GenerationSpec(output_format=ArtifactFormat.pptx, title="Кораллы"),
            artifact_plan=ArtifactPlan(output_format=ArtifactFormat.pptx, title="Кораллы"),
            warnings=[],
        )


class SuccessfulRenderer:
    output_format = "docx"

    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path

    def render(self, artifact_id: str, plan: ArtifactPlan) -> RenderedArtifact:
        file_path = self.tmp_path / f"{artifact_id}.docx"
        file_path.write_bytes(b"docx")
        return RenderedArtifact(
            file_name=file_path.name,
            file_path=file_path,
            file_size=file_path.stat().st_size,
        )


class FailingRenderer:
    output_format = "docx"

    def render(self, artifact_id: str, plan: ArtifactPlan) -> RenderedArtifact:
        raise OSError("disk is not writable")


class RendererRegistryStub:
    def __init__(self, renderer) -> None:
        self.renderer = renderer

    def get(self, output_format: str):
        return self.renderer


def test_generation_pipeline_returns_success_for_planned_docx(tmp_path) -> None:
    pipeline = GenerationPipeline(
        planner=SuccessfulPlanner(),
        renderers=RendererRegistryStub(SuccessfulRenderer(tmp_path)),
    )

    result = pipeline.run(
        "art_123",
        DocumentCreateRequest(prompt="Сделай план встречи"),
    )

    assert isinstance(result, PipelineSuccess)
    assert result.planning.artifact_plan.title == "План встречи"
    assert result.rendered_artifact.file_name == "art_123.docx"
    assert result.rendered_artifact.file_size == 4


def test_generation_pipeline_returns_planning_failure_for_openrouter_error(tmp_path) -> None:
    pipeline = GenerationPipeline(
        planner=FailingPlanner(),
        renderers=RendererRegistryStub(SuccessfulRenderer(tmp_path)),
    )

    result = pipeline.run(
        "art_123",
        DocumentCreateRequest(prompt="Сделай план встречи"),
    )

    assert isinstance(result, PipelineFailure)
    assert result.stage == "planning"
    assert result.user_message == "Не удалось подготовить план документа"
    assert result.technical_message == "OpenRouter unavailable"
    assert result.planning is None


def test_generation_pipeline_returns_rendering_failure_with_planning_snapshot() -> None:
    pipeline = GenerationPipeline(
        planner=SuccessfulPlanner(),
        renderers=RendererRegistryStub(FailingRenderer()),
    )

    result = pipeline.run(
        "art_123",
        DocumentCreateRequest(prompt="Сделай план встречи"),
    )

    assert isinstance(result, PipelineFailure)
    assert result.stage == "rendering"
    assert result.user_message == "Не удалось создать файл документа"
    assert result.technical_message == "disk is not writable"
    assert result.planning is not None
    assert result.planning.artifact_plan.title == "План встречи"


def test_generation_pipeline_reports_unsupported_renderer_format() -> None:
    pipeline = GenerationPipeline(planner=PptxPlanner())

    result = pipeline.run(
        "art_123",
        DocumentCreateRequest(prompt="Сделай презентацию о кораллах"),
    )

    assert isinstance(result, PipelineFailure)
    assert result.stage == "rendering"
    assert result.user_message == "Формат 'pptx' пока не поддерживается"
    assert "Renderer for 'pptx' is not configured." in result.technical_message
