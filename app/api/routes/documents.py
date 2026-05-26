from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import verify_internal_token
from app.db.session import get_db_session
from app.repositories.artifact_repository import ArtifactRepository
from app.schemas.document import DocumentCreateRequest, DocumentCreateResponse, DocumentInfoResponse
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
    status_code=status.HTTP_201_CREATED,
)
def create_document(
    payload: DocumentCreateRequest,
    db_session: Annotated[Session, Depends(get_db_session)],
) -> DocumentCreateResponse:
    service = GenerationService(db_session)
    return service.create_processing_artifact(payload)


@router.get("/{document_id}", response_model=DocumentInfoResponse)
def get_document(
    document_id: str,
    db_session: Annotated[Session, Depends(get_db_session)],
) -> DocumentInfoResponse:
    artifact = ArtifactRepository(db_session).get_by_id(document_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    download_url = None
    if artifact.status == "ready":
        download_url = f"/documents/{artifact.id}/download"

    return DocumentInfoResponse(
        document_id=artifact.id,
        request_id=artifact.request_id,
        status=artifact.status,
        output_format=artifact.output_format,
        file_name=artifact.file_name,
        download_url=download_url,
        error_message=artifact.error_message,
        warnings=artifact.warnings,
    )


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
