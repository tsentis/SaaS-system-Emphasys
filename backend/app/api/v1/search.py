"""Search endpoints: faceted keyword search and semantic search."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.ai.embedder import Embedder, get_embedder
from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.schemas.project import ProjectOut
from app.services import search_service

router = APIRouter(tags=["search"])


@router.get("/projects", response_model=list[ProjectOut])
def search_projects(
    q: str | None = None,
    programme: str | None = None,
    country: str | None = None,
    status: str | None = None,
    min_budget: float | None = None,
    max_budget: float | None = None,
    starts_after: date | None = None,
    ends_before: date | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> list[ProjectOut]:
    projects = search_service.search_projects(
        db,
        q=q,
        programme=programme,
        country=country,
        status=status,
        min_budget=min_budget,
        max_budget=max_budget,
        starts_after=starts_after,
        ends_before=ends_before,
    )
    return [ProjectOut.model_validate(p) for p in projects]


@router.get("/semantic", response_model=list[ProjectOut])
def semantic_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    embedder: Embedder = Depends(get_embedder),
    _: CurrentUser = Depends(get_current_user),
) -> list[ProjectOut]:
    projects = search_service.semantic_search(db, embedder, q=q, limit=limit)
    return [ProjectOut.model_validate(p) for p in projects]
