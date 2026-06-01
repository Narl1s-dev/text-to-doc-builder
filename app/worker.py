import logging
import time

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import init_db
from app.services.document_worker import DocumentWorker


logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    settings.artifact_storage_path.mkdir(parents=True, exist_ok=True)
    init_db()

    worker = DocumentWorker(settings)
    worker.start()
    logger.info("Standalone document worker is running")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Standalone document worker shutdown requested")
    finally:
        worker.stop()


if __name__ == "__main__":
    main()
