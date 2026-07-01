"""Analytics / dashboard endpoints (JSON aggregates for the future charting UI)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.services import analytics_service

router = APIRouter(tags=["analytics"])


@router.get("/summary")
def summary(
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> dict:
    return analytics_service.summary(db, current.tenant_id)


@router.get("/projects-by-programme")
def projects_by_programme(
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    return analytics_service.projects_by_programme(db, current.tenant_id)


@router.get("/organizations-by-country")
def organizations_by_country(
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    return analytics_service.organizations_by_country(db, current.tenant_id)


@router.get("/status")
def status_breakdown(
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> dict:
    return analytics_service.status_breakdown(db, current.tenant_id)


@router.get("/budget")
def budget(
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> dict:
    return analytics_service.budget_stats(db, current.tenant_id)


@router.get("/timeline")
def timeline(
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    return analytics_service.projects_by_year(db, current.tenant_id)
