"""Users, roles, and the user-role association (RBAC)."""

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPrimaryKey


class User(Base, UUIDPrimaryKey, TenantScoped, Timestamped):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email"),)

    # Maps to the external Clerk user id; authorization stays in our DB.
    auth_provider_id: Mapped[str | None] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(nullable=False, index=True)
    full_name: Mapped[str | None] = mapped_column()
    status: Mapped[str] = mapped_column(default="active", nullable=False)


class Role(Base, UUIDPrimaryKey):
    __tablename__ = "roles"

    # System-wide role catalogue (admin, analyst, viewer, …).
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column()


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
