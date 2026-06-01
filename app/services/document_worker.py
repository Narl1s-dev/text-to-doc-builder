import logging
import threading

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_engine
from app.repositories.document_job_repository import DocumentJobRepository
from app.services.generation_service import GenerationService


logger = logging.getLogger(__name__)


class DocumentWorker:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        concurrency: int | None = None,
        poll_interval_seconds: float | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.concurrency = concurrency or self.settings.worker_concurrency
        self.poll_interval_seconds = (
            poll_interval_seconds or self.settings.worker_poll_interval_seconds
        )
        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        if self._threads:
            return

        recovered_count = self.recover_processing_jobs()
        if recovered_count:
            logger.info("Requeued %s processing document job(s)", recovered_count)

        self._stop_event.clear()
        for index in range(self.concurrency):
            thread = threading.Thread(
                target=self._run_loop,
                name=f"document-worker-{index + 1}",
                daemon=True,
            )
            thread.start()
            self._threads.append(thread)

        logger.info("Document worker started with concurrency=%s", self.concurrency)

    def stop(self, timeout_seconds: float = 5.0) -> None:
        self._stop_event.set()
        for thread in self._threads:
            thread.join(timeout=timeout_seconds)
        self._threads.clear()
        logger.info("Document worker stopped")

    def run_once(self) -> bool:
        with Session(bind=get_engine(), autoflush=False, autocommit=False, future=True) as db_session:
            job_id = DocumentJobRepository(db_session).claim_next_queued()

        if job_id is None:
            return False

        logger.info("Processing document job %s", job_id)
        try:
            with Session(
                bind=get_engine(),
                autoflush=False,
                autocommit=False,
                future=True,
            ) as db_session:
                GenerationService(db_session).process_job(job_id)
        except Exception:
            logger.exception("Document job %s crashed outside controlled failure handling", job_id)
        return True

    def recover_processing_jobs(self) -> int:
        with Session(bind=get_engine(), autoflush=False, autocommit=False, future=True) as db_session:
            count = DocumentJobRepository(db_session).requeue_processing_jobs()
            db_session.commit()
            return count

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            processed_job = self.run_once()
            if not processed_job:
                self._stop_event.wait(self.poll_interval_seconds)
