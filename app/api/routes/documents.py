from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import verify_internal_token
from app.db.session import get_db_session
from app.repositories.artifact_repository import ArtifactRepository
from app.schemas.document import DocumentCreateRequest, DocumentCreateResponse, DocumentInfoResponse
from app.schemas.formats import (
    infer_artifact_format_from_prompt,
    is_render_supported,
    supported_render_format_values,
)
from app.services.generation_service import GenerationService
from app.services.storage_service import StorageService


router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(verify_internal_token)],
)


@router.post(
    "",
    response_model=DocumentCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_document(
    payload: DocumentCreateRequest,
    db_session: Annotated[Session, Depends(get_db_session)],
) -> DocumentCreateResponse:
    inferred_format = infer_artifact_format_from_prompt(payload.prompt)
    if payload.output_format is None and inferred_format is not None and not is_render_supported(inferred_format):
        supported_formats = ", ".join(supported_render_format_values())
        raise HTTPException(
            status_code=422,
            detail=(
                f"Output format '{inferred_format}' was inferred from the prompt, "
                f"but is not supported yet. Supported formats: {supported_formats}."
            ),
        )

    service = GenerationService(db_session)
    return service.enqueue_document(payload)


@router.get("/{document_id}", response_model=DocumentInfoResponse)
def get_document(
    document_id: str,
    db_session: Annotated[Session, Depends(get_db_session)],
) -> DocumentInfoResponse:
    document = GenerationService(db_session).get_document_info(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return document


@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    db_session: Annotated[Session, Depends(get_db_session)],
) -> FileResponse:
    artifact = ArtifactRepository(db_session).get_by_id(document_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if artifact.status != "ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document is not ready")

    try:
        file_path = StorageService().get_artifact_file_path(artifact)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found",
        ) from exc

    return FileResponse(
        path=file_path,
        filename=artifact.file_name or f"{artifact.id}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
