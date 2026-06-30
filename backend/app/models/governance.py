"""Audit log, GDPR requests, and API keys (security & compliance)."""

import uuid

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPrimaryKey


class AuditLog(Base, UUIDPrimaryKey, TenantScoped, Timestamped):
    __tablename__ = "audit_log"

    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    action: Mapped[str] = mapped_column(nullable=False)  # e.g. document.upload
    entity: Mapped[str | None] = mapped_column()
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    ip_address: Mapped[str | None] = mapped_column()


class GdprRequest(Base, UUIDPrimaryKey, TenantScoped, Timestamped):
    __tablename__ = "gdpr_requests"

    subject_email: Mapped[str] = mapped_column(nullable=False)
    request_type: Mapped[str] = mapped_column(nullable=False)  # access | erasure
    status: Mapped[str] = mapped_column(default="pending", nullable=False)


class ApiKey(Base, UUIDPrimaryKey, TenantScoped, Timestamped):
    __tablename__ = "api_keys"

    name: Mapped[str] = mapped_column(nullable=False)
    hashed_key: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    scopes: Mapped[str | None] = mapped_column()  # comma-separated scopes
    last_used_at: Mapped[str | None] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
