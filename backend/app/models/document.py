"""Uploaded documents and AI analysis runs."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPrimaryKey


class Document(Base, UUIDPrimaryKey, TenantScoped, Timestamped):
    __tablename__ = "documents"

    filename: Mapped[str] = mapped_column(nullable=False)
    s3_key: Mapped[str] = mapped_column(nullable=False)
    sha256: Mapped[str | None] = mapped_column(index=True)
    mime_type: Mapped[str | None] = mapped_column()
    page_count: Mapped[int | None] = mapped_column()
    size_bytes: Mapped[int | None] = mapped_column()
    # uploaded | processing | done | failed
    status: Mapped[str] = mapped_column(default="uploaded", nullable=False, index=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    # Soft delete: non-null means the document is hidden from listings.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AnalysisRun(Base, UUIDPrimaryKey, TenantScoped, Timestamped):
    __tablename__ = "analysis_runs"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    model: Mapped[str | None] = mapped_column()
    prompt_version: Mapped[str | None] = mapped_column()
    status: Mapped[str] = mapped_column(default="queued", nullable=False)
    cost_input_tokens: Mapped[int | None] = mapped_column()
    cost_output_tokens: Mapped[int | None] = mapped_column()
    error: Mapped[str | None] = mapped_column()
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
