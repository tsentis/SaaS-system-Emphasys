"""Projects extracted from proposals, plus partner links and work packages."""

import uuid
from datetime import date

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPrimaryKey


class Project(Base, UUIDPrimaryKey, TenantScoped, Timestamped):
    __tablename__ = "projects"

    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), index=True
    )
    programme_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programmes.id", ondelete="SET NULL")
    )
    call_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("funding_calls.id", ondelete="SET NULL")
    )
    acronym: Mapped[str | None] = mapped_column(index=True)
    title: Mapped[str | None] = mapped_column()
    summary: Mapped[str | None] = mapped_column()
    total_budget: Mapped[float | None] = mapped_column(Numeric(18, 2))
    start_date: Mapped[date | None] = mapped_column()
    end_date: Mapped[date | None] = mapped_column()
    status: Mapped[str] = mapped_column(default="draft", nullable=False, index=True)
    # Aggregate confidence of the AI extraction (0..1).
    extraction_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))


class ProjectPartner(Base, UUIDPrimaryKey, TenantScoped, Timestamped):
    __tablename__ = "project_partners"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )
    role: Mapped[str | None] = mapped_column()  # coordinator | partner
    budget_share: Mapped[float | None] = mapped_column(Numeric(18, 2))


class WorkPackage(Base, UUIDPrimaryKey, TenantScoped, Timestamped):
    __tablename__ = "work_packages"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[int | None] = mapped_column()
    title: Mapped[str | None] = mapped_column()
    lead_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL")
    )
    budget: Mapped[float | None] = mapped_column(Numeric(18, 2))
