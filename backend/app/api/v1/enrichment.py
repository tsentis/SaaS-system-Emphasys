"""Project enrichment endpoints (mounted under /projects)."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user, require_roles
from app.core.roles import ADMIN, ANALYST
from app.enrichment.sources import get_enrichment_registry
from app.services import enrichment_service, project_service

router = APIRouter(tags=["enrichment"])


class EnrichmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    payload: dict
    created_at: datetime


class EnrichmentResult(BaseModel):
    matched: bool
    record: EnrichmentOut | None = None


@router.post("/{project_id}/enrich", response_model=EnrichmentResult)
def enrich_project(
    project_id: uuid.UUID,
    source: str = Query("cordis"),
    db: Session = Depends(get_db),
    registry: dict = Depends(get_enrichment_registry),
    _: CurrentUser = Depends(require_roles(ADMIN, ANALYST)),
) -> EnrichmentResult:
    project = project_service.get_project(db, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if source not in registry:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unknown source '{source}'. Available: {sorted(registry)}",
        )
    record = enrichment_service.enrich_project(db, registry[source], project=project)
    if record is None:
        return EnrichmentResult(matched=False)
    return EnrichmentResult(matched=True, record=EnrichmentOut.model_validate(record))


@router.get("/{project_id}/enrichment", response_model=list[EnrichmentOut])
def list_enrichment(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> list[EnrichmentOut]:
    return [
        EnrichmentOut.model_validate(e)
        for e in enrichment_service.list_for_project(db, project_id)
    ]
