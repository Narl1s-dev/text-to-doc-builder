from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import init_db
from app.services.document_worker import DocumentWorker


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    settings.artifact_storage_path.mkdir(parents=True, exist_ok=True)
    init_db()
    app.state.settings = settings
    app.state.document_worker = None
    if settings.worker_enabled:
        app.state.document_worker = DocumentWorker(settings)
        app.state.document_worker.start()

    logger.info("Application startup complete")
    try:
        yield
    finally:
        if app.state.document_worker is not None:
            app.state.document_worker.stop()
        logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    app.include_router(api_router)
    return app


app = create_app()
