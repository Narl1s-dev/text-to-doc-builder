from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Artifact, DocumentJob, GenerationRequest
from app.repositories.artifact_repository import ArtifactRepository
from app.repositories.document_job_repository import DocumentJobRepository
from app.repositories.generation_request_repository import GenerationRequestRepository
from app.repositories.llm_generation_repository import LLMGenerationRepository
from app.schemas.document import DocumentCreateRequest, DocumentCreateResponse, DocumentInfoResponse
from app.services.generation_pipeline import GenerationPipeline, PipelineFailure, PlanningSnapshot
from app.services.prompt_builder import PromptBuilder


class GenerationService:
    def __init__(self, db_session: Session, pipeline: GenerationPipeline | None = None) -> None:
        self.db_session = db_session
        self.requests = GenerationRequestRepository(db_session)
        self.artifacts = ArtifactRepository(db_session)
        self.jobs = DocumentJobRepository(db_session)
        self.llm_generations = LLMGenerationRepository(db_session)
        self.settings = get_settings()
        self.pipeline = pipeline or GenerationPipeline(self.settings)

    def enqueue_document(self, payload: DocumentCreateRequest) -> DocumentCreateResponse:
        generation_request = self.requests.create(payload)
        artifact = self.artifacts.create_queued(
            request_id=generation_request.id,
            output_format=payload.requested_output_format,
            title=_extract_title(payload.overrides),
        )
        job = self.jobs.create_queued(
            request_id=generation_request.id,
            artifact_id=artifact.id,
        )

        response = _to_create_response(artifact, generation_request.id, job)
        self.db_session.commit()
        return response

    def get_document_info(self, document_id: str) -> DocumentInfoResponse | None:
        artifact = self.artifacts.get_by_id(document_id)
        if artifact is None:
            return None

        job = self.jobs.get_by_artifact_id(artifact.id)
        return _to_info_response(artifact, artifact.request_id, job)

    def process_job(self, job_id: str) -> None:
        job = self.jobs.get_by_id(job_id)
        if job is None:
            return

        artifact = job.artifact
        generation_request = job.request
        payload = _to_payload(generation_request)

        artifact = self.artifacts.mark_processing(artifact)
        job = self.jobs.mark_processing(job, current_stage="generation")
        self.db_session.commit()

        try:
            pipeline_result = self.pipeline.run(artifact.id, payload)
        except Exception as exc:
            self._record_unexpected_failure(job_id, str(exc))
            return

        job = self.jobs.get_by_id(job_id)
        if job is None:
            return
        artifact = job.artifact

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
            self.jobs.mark_failed(
                job,
                error_message=pipeline_result.user_message,
                current_stage=pipeline_result.stage,
            )
            self.db_session.commit()
            return

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
        self.artifacts.mark_ready(
            artifact,
            file_name=pipeline_result.rendered_artifact.file_name,
            file_path=str(pipeline_result.rendered_artifact.file_path),
            file_size=pipeline_result.rendered_artifact.file_size,
            warnings=pipeline_result.planning.warnings,
        )
        self.jobs.mark_ready(job)
        self.db_session.commit()

    def _record_unexpected_failure(self, job_id: str, technical_message: str) -> None:
        self.db_session.rollback()
        job = self.jobs.get_by_id(job_id)
        if job is None:
            return

        self.artifacts.mark_failed(
            job.artifact,
            error_message="РќРµ СѓРґР°Р»РѕСЃСЊ СЃРѕР·РґР°С‚СЊ С„Р°Р№Р» РґРѕРєСѓРјРµРЅС‚Р°",
            warnings=[technical_message],
        )
        self.jobs.mark_failed(
            job,
            error_message=technical_message,
            current_stage="worker",
        )
        self.db_session.commit()

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
            raw_output=failure.raw_output,
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


def _to_payload(generation_request: GenerationRequest) -> DocumentCreateRequest:
    metadata = dict(generation_request.metadata_json or {})
    output_format = None
    if metadata.pop("_requested_output_format_explicit", False):
        output_format = generation_request.requested_output_format

    return DocumentCreateRequest(
        prompt=generation_request.prompt,
        output_format=output_format,
        overrides=generation_request.overrides,
        metadata=metadata,
    )


def _document_status(artifact: Artifact, job: DocumentJob | None) -> str:
    if job is not None and job.status in {"queued", "processing", "canceled"}:
        return job.status
    if artifact.status in {"ready", "failed", "canceled"}:
        return artifact.status
    if job is not None:
        return job.status
    return artifact.status


def _document_payload(artifact: Artifact, request_id: str, job: DocumentJob | None) -> dict:
    download_url = None
    if artifact.status == "ready":
        download_url = f"/documents/{artifact.id}/download"

    return {
        "document_id": artifact.id,
        "request_id": request_id,
        "job_id": job.id if job is not None else None,
        "status": _document_status(artifact, job),
        "current_stage": job.current_stage if job is not None else artifact.status,
        "output_format": artifact.output_format,
        "file_name": artifact.file_name,
        "status_url": f"/documents/{artifact.id}",
        "download_url": download_url,
        "error_message": artifact.error_message or (job.error_message if job is not None else None),
        "warnings": artifact.warnings,
    }


def _to_create_response(
    artifact: Artifact,
    request_id: str,
    job: DocumentJob | None,
) -> DocumentCreateResponse:
    return DocumentCreateResponse(**_document_payload(artifact, request_id, job))


def _to_info_response(
    artifact: Artifact,
    request_id: str,
    job: DocumentJob | None,
) -> DocumentInfoResponse:
    return DocumentInfoResponse(**_document_payload(artifact, request_id, job))
