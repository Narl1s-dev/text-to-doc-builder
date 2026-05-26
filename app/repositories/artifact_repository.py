from sqlalchemy.orm import Session

from app.db.models import Artifact


class ArtifactRepository:
    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def create_processing(self, request_id: str, output_format: str, title: str | None) -> Artifact:
        artifact = Artifact(
            request_id=request_id,
            output_format=output_format,
            status="processing",
            title=title,
            warnings=[],
        )
        self.db_session.add(artifact)
        self.db_session.flush()
        return artifact

    def update_planning(self, artifact: Artifact, title: str | None, warnings: list[str]) -> Artifact:
        artifact.title = title
        artifact.warnings = warnings
        self.db_session.flush()
        return artifact

    def update_planned_format(
        self,
        artifact: Artifact,
        *,
        output_format: str,
        title: str | None,
    ) -> Artifact:
        artifact.output_format = output_format
        artifact.title = title
        self.db_session.flush()
        return artifact

    def mark_ready(
        self,
        artifact: Artifact,
        *,
        file_name: str,
        file_path: str,
        file_size: int,
        warnings: list[str],
    ) -> Artifact:
        artifact.status = "ready"
        artifact.file_name = file_name
        artifact.file_path = file_path
        artifact.file_size = file_size
        artifact.error_message = None
        artifact.warnings = warnings
        self.db_session.flush()
        return artifact

    def mark_failed(self, artifact: Artifact, error_message: str, warnings: list[str]) -> Artifact:
        artifact.status = "failed"
        artifact.error_message = error_message
        artifact.warnings = warnings
        self.db_session.flush()
        return artifact

    def get_by_id(self, artifact_id: str) -> Artifact | None:
        return self.db_session.get(Artifact, artifact_id)
