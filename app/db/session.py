from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    connect_args = {}
    engine_kwargs = {}

    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

        if settings.database_url != "sqlite:///:memory:":
            database_path = settings.database_url.removeprefix("sqlite:///")
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        else:
            engine_kwargs["poolclass"] = StaticPool

    return create_engine(
        settings.database_url,
        connect_args=connect_args,
        future=True,
        **engine_kwargs,
    )

def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())


def get_db_session() -> Iterator[Session]:
    db_session = Session(bind=get_engine(), autoflush=False, autocommit=False, future=True)
    try:
        yield db_session
    finally:
        db_session.close()
