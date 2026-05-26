from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class GenerationRequest(Base):
    __tablename__ = "generation_requests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("req"))
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    requested_output_format: Mapped[str] = mapped_column(String(32), nullable=False, default="docx")
    overrides: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="request",
        cascade="all, delete-orphan",
    )
    llm_generations: Mapped[list["LLMGeneration"]] = relationship(
        back_populates="request",
        cascade="all, delete-orphan",
    )


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("art"))
    request_id: Mapped[str] = mapped_column(
        ForeignKey("generation_requests.id"),
        nullable=False,
        index=True,
    )
    output_format: Mapped[str] = mapped_column(String(32), nullable=False, default="docx")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="processing")
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    request: Mapped[GenerationRequest] = relationship(back_populates="artifacts")


class LLMGeneration(Base):
    __tablename__ = "llm_generations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("llm"))
    request_id: Mapped[str] = mapped_column(
        ForeignKey("generation_requests.id"),
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="openrouter")
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    input_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    raw_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    request: Mapped[GenerationRequest] = relationship(back_populates="llm_generations")
