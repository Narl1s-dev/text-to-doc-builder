from sqlalchemy.orm import Session

from app.db.models import GenerationRequest
from app.schemas.document import DocumentCreateRequest


class GenerationRequestRepository:
    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def create(self, payload: DocumentCreateRequest) -> GenerationRequest:
        request = GenerationRequest(
            prompt=payload.prompt,
            requested_output_format=payload.requested_output_format,
            overrides=payload.overrides,
            metadata_json=payload.metadata,
        )
        self.db_session.add(request)
        self.db_session.flush()
        return request
