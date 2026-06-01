from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import Artifact, DocumentJob, utc_now


class DocumentJobRepository:
    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def create_queued(self, request_id: str, artifact_id: str) -> DocumentJob:
        job = DocumentJob(
            request_id=request_id,
            artifact_id=artifact_id,
            status="queued",
            current_stage="queued",
        )
        self.db_session.add(job)
        self.db_session.flush()
        return job

    def get_by_id(self, job_id: str) -> DocumentJob | None:
        return self.db_session.get(DocumentJob, job_id)

    def get_by_artifact_id(self, artifact_id: str) -> DocumentJob | None:
        return self.db_session.execute(
            select(DocumentJob).where(DocumentJob.artifact_id == artifact_id)
        ).scalar_one_or_none()

    def claim_next_queued(self) -> str | None:
        job_id = self.db_session.execute(
            select(DocumentJob.id)
            .where(DocumentJob.status == "queued")
            .order_by(DocumentJob.created_at)
            .limit(1)
        ).scalar_one_or_none()
        if job_id is None:
            return None

        now = utc_now()
        result = self.db_session.execute(
            update(DocumentJob)
            .where(DocumentJob.id == job_id, DocumentJob.status == "queued")
            .values(
                status="processing",
                current_stage="starting",
                attempts=DocumentJob.attempts + 1,
                error_message=None,
                started_at=now,
                finished_at=None,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            self.db_session.rollback()
            return None

        self.db_session.commit()
        return job_id

    def mark_processing(self, job: DocumentJob, *, current_stage: str) -> DocumentJob:
        job.status = "processing"
        job.current_stage = current_stage
        job.error_message = None
        job.finished_at = None
        self.db_session.flush()
        return job

    def mark_ready(self, job: DocumentJob) -> DocumentJob:
        job.status = "ready"
        job.current_stage = "completed"
        job.error_message = None
        job.finished_at = utc_now()
        self.db_session.flush()
        return job

    def mark_failed(
        self,
        job: DocumentJob,
        *,
        error_message: str,
        current_stage: str,
    ) -> DocumentJob:
        job.status = "failed"
        job.current_stage = current_stage
        job.error_message = error_message
        job.finished_at = utc_now()
        self.db_session.flush()
        return job

    def requeue_processing_jobs(self) -> int:
        jobs = self.db_session.execute(
            select(DocumentJob).where(DocumentJob.status == "processing")
        ).scalars()
        count = 0
        for job in jobs:
            job.status = "queued"
            job.current_stage = "queued"
            job.started_at = None
            job.finished_at = None
            job.error_message = None
            if isinstance(job.artifact, Artifact) and job.artifact.status == "processing":
                job.artifact.status = "queued"
            count += 1

        self.db_session.flush()
        return count
