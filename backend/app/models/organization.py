"""Partner organizations (registry) and their contact persons."""

import uuid

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPrimaryKey


class Organization(Base, UUIDPrimaryKey, TenantScoped, Timestamped):
    """A partner organization extracted from proposals. Deduplicated within a tenant
    via ``normalized_key`` (and PIC number where available)."""

    __tablename__ = "organizations"

    legal_name: Mapped[str] = mapped_column(nullable=False)
    normalized_key: Mapped[str] = mapped_column(index=True, nullable=False)
    pic_number: Mapped[str | None] = mapped_column(index=True)
    country: Mapped[str | None] = mapped_column()
    org_type: Mapped[str | None] = mapped_column()  # NGO, university, SME, public, …
    website: Mapped[str | None] = mapped_column()


class Person(Base, UUIDPrimaryKey, TenantScoped, Timestamped):
    __tablename__ = "persons"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL")
    )
    full_name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str | None] = mapped_column()
    role: Mapped[str | None] = mapped_column()
