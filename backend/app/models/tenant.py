"""Tenant (SaaS customer organization)."""

from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPrimaryKey


class Tenant(Base, UUIDPrimaryKey, Timestamped):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(nullable=False)
    slug: Mapped[str] = mapped_column(unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(default="free", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
