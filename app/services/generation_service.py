from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories.artifact_repository import ArtifactRepository
from app.repositories.generation_request_repository import GenerationRequestRepository
from app.repositories.llm_generation_repository import LLMGenerationRepository
from app.schemas.document import DocumentCreateRequest, DocumentCreateResponse
from app.services.generation_pipeline import GenerationPipeline, PipelineFailure, PlanningSnapshot
from app.services.prompt_builder import PromptBuilder


class GenerationService:
    def __init__(self, db_session: Session, pipeline: GenerationPipeline | None = None) -> None:
        self.db_session = db_session
        self.requests = GenerationRequestRepository(db_session)
        self.artifacts = ArtifactRepository(db_session)
        self.llm_generations = LLMGenerationRepository(db_session)
        self.settings = get_settings()
        self.pipeline = pipeline or GenerationPipeline(self.settings)

    def create_processing_artifact(self, payload: DocumentCreateRequest) -> DocumentCreateResponse:
        generation_request = self.requests.create(payload)
        artifact = self.artifacts.create_processing(
            request_id=generation_request.id,
            output_format=payload.requested_output_format,
            title=_extract_title(payload.overrides),
        )

        pipeline_result = self.pipeline.run(artifact.id, payload)
        if isinstance(pipeline_result, PipelineFailure):
            self._record_pipeline_failure(generation_request.id, payload, pipeline_result)
            if pipeline_result.planning is not None:
                artifact = self.artifacts.update_planned_format(
                    artifact,
                    output_format=pipeline_result.planning.artifact_plan.output_format,
                    title=pipeline_result.planning.artifact_plan.title,
                )
            artifact = self.artifacts.mark_failed(
                artifact,
                error_message=pipeline_result.user_message,
                warnings=pipeline_result.warnings,
            )
            self.db_session.commit()
            return _to_response(artifact, generation_request.id)

        self._record_planning_snapshot(
            generation_request.id,
            payload,
            pipeline_result.planning,
        )
        artifact = self.artifacts.update_planning(
            artifact,
            title=pipeline_result.planning.artifact_plan.title,
            warnings=pipeline_result.planning.warnings,
        )
        artifact = self.artifacts.mark_ready(
            artifact,
            file_name=pipeline_result.rendered_artifact.file_name,
            file_path=str(pipeline_result.rendered_artifact.file_path),
            file_size=pipeline_result.rendered_artifact.file_size,
            warnings=pipeline_result.planning.warnings,
        )
        self.db_session.commit()

        return _to_response(artifact, generation_request.id)

    def _record_pipeline_failure(
        self,
        request_id: str,
        payload: DocumentCreateRequest,
        failure: PipelineFailure,
    ) -> None:
        if failure.planning is not None:
            self._record_planning_snapshot(request_id, payload, failure.planning)
            return

        self.llm_generations.create(
            request_id=request_id,
            stage=failure.stage,
            provider="openrouter",
            model=self.settings.openrouter_model,
            prompt_version=PromptBuilder.prompt_version,
            input_payload=payload.model_dump(mode="json"),
            raw_output=None,
            parsed_output=None,
            error_message=failure.technical_message,
        )

    def _record_planning_snapshot(
        self,
        request_id: str,
        payload: DocumentCreateRequest,
        planning: PlanningSnapshot,
    ) -> None:
        self.llm_generations.create(
            request_id=request_id,
            stage="planning",
            provider="openrouter",
            model=self.settings.openrouter_model,
            prompt_version=PromptBuilder.prompt_version,
            input_payload=payload.model_dump(mode="json"),
            raw_output=planning.raw_output,
            parsed_output=planning.parsed_output,
            error_message=planning.skipped_reason,
        )


def _extract_title(overrides: dict) -> str | None:
    title = overrides.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return None


def _to_response(artifact, request_id: str) -> DocumentCreateResponse:
    download_url = None
    if artifact.status == "ready":
        download_url = f"/documents/{artifact.id}/download"

    return DocumentCreateResponse(
        document_id=artifact.id,
        request_id=request_id,
        status=artifact.status,
        output_format=artifact.output_format,
        file_name=artifact.file_name,
        download_url=download_url,
        error_message=artifact.error_message,
        warnings=artifact.warnings,
    )
