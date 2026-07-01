"""Persist external enrichment payloads for projects."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enrichment.base import EnrichmentSource
from app.models.enrichment import ExternalEnrichment
from app.models.project import Project


def enrich_project(
    db: Session, source: EnrichmentSource, *, project: Project
) -> ExternalEnrichment | None:
    payload = source.enrich(title=project.title, acronym=project.acronym)
    if payload is None:
        return None
    record = ExternalEnrichment(
        tenant_id=project.tenant_id,
        owner_type="project",
        owner_id=project.id,
        source=source.name,
        payload=payload,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_for_project(db: Session, project_id: uuid.UUID) -> list[ExternalEnrichment]:
    return list(
        db.execute(
            select(ExternalEnrichment)
            .where(
                ExternalEnrichment.owner_type == "project",
                ExternalEnrichment.owner_id == project_id,
            )
            .order_by(ExternalEnrichment.created_at.desc())
        ).scalars()
    )
