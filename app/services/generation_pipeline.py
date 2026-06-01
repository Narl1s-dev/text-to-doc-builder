from dataclasses import dataclass, replace
from pathlib import Path

from app.core.config import Settings, get_settings
from app.llm.artifact_planner import LLMArtifactPlanner
from app.llm.openrouter_client import OpenRouterError
from app.llm.response_validator import LLMResponseValidationError
from app.renderers.base import RenderedArtifact
from app.renderers.registry import RendererRegistry, UnsupportedRendererError
from app.schemas.artifact_plan import ArtifactPlan
from app.schemas.document import DocumentCreateRequest
from app.schemas.document_spec import DocumentSpec, document_spec_from_plan
from app.schemas.formats import is_render_supported
from app.schemas.generation_spec import GenerationSpec


@dataclass(frozen=True)
class PlanningSnapshot:
    generation_spec: GenerationSpec
    document_spec: DocumentSpec
    artifact_plan: ArtifactPlan
    warnings: list[str]
    raw_output: str | None
    skipped_reason: str | None
    document_spec_path: str | None = None

    @property
    def parsed_output(self) -> dict:
        return {
            "generation_spec": self.generation_spec.model_dump(mode="json"),
            "document_spec": self.document_spec.model_dump(mode="json"),
            "artifact_plan": self.artifact_plan.model_dump(mode="json"),
            "warnings": self.warnings,
            "document_spec_path": self.document_spec_path,
        }


@dataclass(frozen=True)
class PipelineSuccess:
    planning: PlanningSnapshot
    rendered_artifact: RenderedArtifact
    document_spec_path: Path | None = None


@dataclass(frozen=True)
class PipelineFailure:
    stage: str
    user_message: str
    technical_message: str
    warnings: list[str]
    planning: PlanningSnapshot | None = None
    raw_output: str | None = None


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

        planning_result = self._save_document_spec(artifact_id, planning_result)
        if isinstance(planning_result, PipelineFailure):
            return planning_result

        format_failure = self._validate_planned_format(planning_result)
        if format_failure is not None:
            return format_failure

        try:
            renderer = self.renderers.get(planning_result.document_spec.output_format)
        except UnsupportedRendererError as exc:
            return PipelineFailure(
                stage="rendering",
                user_message=(
                    f"Формат '{planning_result.document_spec.output_format}' пока не поддерживается"
                ),
                technical_message=str(exc),
                warnings=[*planning_result.warnings, str(exc)],
                planning=planning_result,
            )

        try:
            rendered_artifact = renderer.render(artifact_id, planning_result.document_spec)
        except Exception as exc:
            return PipelineFailure(
                stage="rendering",
                user_message="Не удалось создать файл документа",
                technical_message=str(exc),
                warnings=[*planning_result.warnings, str(exc)],
                planning=planning_result,
            )

        if rendered_artifact.warnings:
            planning_result = replace(
                planning_result,
                warnings=[*planning_result.warnings, *rendered_artifact.warnings],
            )

        return PipelineSuccess(
            planning=planning_result,
            rendered_artifact=rendered_artifact,
            document_spec_path=(
                Path(planning_result.document_spec_path)
                if planning_result.document_spec_path is not None
                else None
            ),
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
                raw_output=getattr(exc, "raw_output", None),
            )

        return PlanningSnapshot(
            generation_spec=result.generation_spec,
            document_spec=result.document_spec
            or document_spec_from_plan(result.generation_spec, result.artifact_plan),
            artifact_plan=result.artifact_plan,
            warnings=result.warnings,
            raw_output=result.raw_output,
            skipped_reason=result.skipped_reason,
        )

    def _save_document_spec(
        self,
        artifact_id: str,
        planning: PlanningSnapshot,
    ) -> PlanningSnapshot | PipelineFailure:
        try:
            storage_path = self.settings.artifact_storage_path
            storage_path.mkdir(parents=True, exist_ok=True)
            document_spec_path = (storage_path / f"{artifact_id}.document_spec.json").resolve()
            document_spec_path.write_text(
                planning.document_spec.model_dump_json(indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            return PipelineFailure(
                stage="document_spec",
                user_message="Не удалось сохранить спецификацию документа",
                technical_message=str(exc),
                warnings=[*planning.warnings, str(exc)],
                planning=planning,
            )

        return replace(planning, document_spec_path=str(document_spec_path))

    def _validate_planned_format(self, planning: PlanningSnapshot) -> PipelineFailure | None:
        output_format = planning.document_spec.output_format
        if is_render_supported(output_format):
            return None

        technical_message = f"Renderer for '{output_format}' is not configured."
        return PipelineFailure(
            stage="format_validation",
            user_message=f"Формат '{output_format}' пока не поддерживается",
            technical_message=technical_message,
            warnings=[*planning.warnings, technical_message],
            planning=planning,
        )
