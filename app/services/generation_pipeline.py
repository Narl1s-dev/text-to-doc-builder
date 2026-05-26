from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.llm.artifact_planner import LLMArtifactPlanner
from app.llm.openrouter_client import OpenRouterError
from app.llm.response_validator import LLMResponseValidationError
from app.renderers.base import RenderedArtifact
from app.renderers.registry import RendererRegistry, UnsupportedRendererError
from app.schemas.artifact_plan import ArtifactPlan
from app.schemas.document import DocumentCreateRequest
from app.schemas.generation_spec import GenerationSpec


@dataclass(frozen=True)
class PlanningSnapshot:
    generation_spec: GenerationSpec
    artifact_plan: ArtifactPlan
    warnings: list[str]
    raw_output: str | None
    skipped_reason: str | None

    @property
    def parsed_output(self) -> dict:
        return {
            "generation_spec": self.generation_spec.model_dump(mode="json"),
            "artifact_plan": self.artifact_plan.model_dump(mode="json"),
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class PipelineSuccess:
    planning: PlanningSnapshot
    rendered_artifact: RenderedArtifact


@dataclass(frozen=True)
class PipelineFailure:
    stage: str
    user_message: str
    technical_message: str
    warnings: list[str]
    planning: PlanningSnapshot | None = None


PipelineResult = PipelineSuccess | PipelineFailure


class GenerationPipeline:
    def __init__(
        self,
        settings: Settings | None = None,
        planner: LLMArtifactPlanner | None = None,
        renderers: RendererRegistry | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.planner = planner or LLMArtifactPlanner(self.settings)
        self.renderers = renderers or RendererRegistry()

    def run(self, artifact_id: str, payload: DocumentCreateRequest) -> PipelineResult:
        planning_result = self._plan(payload)
        if isinstance(planning_result, PipelineFailure):
            return planning_result

        try:
            renderer = self.renderers.get(planning_result.artifact_plan.output_format)
        except UnsupportedRendererError as exc:
            return PipelineFailure(
                stage="rendering",
                user_message=(
                    f"Формат '{planning_result.artifact_plan.output_format}' пока не поддерживается"
                ),
                technical_message=str(exc),
                warnings=[*planning_result.warnings, str(exc)],
                planning=planning_result,
            )

        try:
            rendered_artifact = renderer.render(artifact_id, planning_result.artifact_plan)
        except Exception as exc:
            return PipelineFailure(
                stage="rendering",
                user_message="Не удалось создать файл документа",
                technical_message=str(exc),
                warnings=[*planning_result.warnings, str(exc)],
                planning=planning_result,
            )

        return PipelineSuccess(
            planning=planning_result,
            rendered_artifact=rendered_artifact,
        )

    def _plan(self, payload: DocumentCreateRequest) -> PlanningSnapshot | PipelineFailure:
        try:
            result = self.planner.plan(payload)
        except (OpenRouterError, LLMResponseValidationError) as exc:
            return PipelineFailure(
                stage="planning",
                user_message="Не удалось подготовить план документа",
                technical_message=str(exc),
                warnings=["LLM planning failed."],
            )

        return PlanningSnapshot(
            generation_spec=result.generation_spec,
            artifact_plan=result.artifact_plan,
            warnings=result.warnings,
            raw_output=result.raw_output,
            skipped_reason=result.skipped_reason,
        )
