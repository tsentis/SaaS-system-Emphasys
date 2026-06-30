"""External enrichment payloads and vector embeddings for semantic search."""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPrimaryKey

# Embedding dimensionality; align with the embedding model chosen in Milestone 5.
EMBEDDING_DIM = 1024


class ExternalEnrichment(Base, UUIDPrimaryKey, TenantScoped, Timestamped):
    __tablename__ = "external_enrichment"

    # Polymorphic owner: a project or an organization.
    owner_type: Mapped[str] = mapped_column(nullable=False)  # project | organization
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    source: Mapped[str] = mapped_column(nullable=False)  # cordis | ft_portal | …
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class Embedding(Base, UUIDPrimaryKey, TenantScoped):
    __tablename__ = "embeddings"

    owner_type: Mapped[str] = mapped_column(nullable=False)  # project | document | …
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    chunk: Mapped[str] = mapped_column(nullable=False)
    vector: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
