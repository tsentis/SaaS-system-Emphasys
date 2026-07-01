"""Aggregate analytics over a tenant's data.

Queries filter on ``tenant_id`` explicitly (in addition to the session guard) because
aggregate correctness matters — a dashboard must never mix tenants.
"""

import uuid

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.organization import Organization
from app.models.programme import Programme
from app.models.project import Project


def summary(db: Session, tenant_id: uuid.UUID) -> dict:
    def count(entity, *extra) -> int:
        return db.execute(
            select(func.count()).select_from(entity).where(
                entity.tenant_id == tenant_id, *extra
            )
        ).scalar_one()

    return {
        "documents": count(Document, Document.deleted_at.is_(None)),
        "projects": count(Project),
        "organizations": count(Organization),
        "programmes": db.execute(
            select(func.count(func.distinct(Project.programme_id))).where(
                Project.tenant_id == tenant_id, Project.programme_id.isnot(None)
            )
        ).scalar_one(),
        "partner_countries": db.execute(
            select(func.count(func.distinct(Organization.country))).where(
                Organization.tenant_id == tenant_id, Organization.country.isnot(None)
            )
        ).scalar_one(),
    }


def projects_by_programme(db: Session, tenant_id: uuid.UUID) -> list[dict]:
    rows = db.execute(
        select(Programme.name, func.count(Project.id))
        .join(Programme, Programme.id == Project.programme_id)
        .where(Project.tenant_id == tenant_id)
        .group_by(Programme.name)
        .order_by(func.count(Project.id).desc())
    ).all()
    return [{"label": name, "count": c} for name, c in rows]


def organizations_by_country(db: Session, tenant_id: uuid.UUID) -> list[dict]:
    rows = db.execute(
        select(Organization.country, func.count())
        .where(Organization.tenant_id == tenant_id, Organization.country.isnot(None))
        .group_by(Organization.country)
        .order_by(func.count().desc())
    ).all()
    return [{"label": country, "count": c} for country, c in rows]


def status_breakdown(db: Session, tenant_id: uuid.UUID) -> dict:
    def by_status(entity, *extra):
        rows = db.execute(
            select(entity.status, func.count())
            .where(entity.tenant_id == tenant_id, *extra)
            .group_by(entity.status)
        ).all()
        return {status: c for status, c in rows}

    return {
        "documents": by_status(Document, Document.deleted_at.is_(None)),
        "projects": by_status(Project),
    }


def budget_stats(db: Session, tenant_id: uuid.UUID) -> dict:
    total, avg, funded = db.execute(
        select(
            func.coalesce(func.sum(Project.total_budget), 0),
            func.avg(Project.total_budget),
            func.count(Project.total_budget),
        ).where(Project.tenant_id == tenant_id)
    ).one()
    return {
        "total_budget": float(total or 0),
        "average_budget": float(avg) if avg is not None else None,
        "projects_with_budget": funded,
    }


def projects_by_year(db: Session, tenant_id: uuid.UUID) -> list[dict]:
    rows = db.execute(
        select(extract("year", Project.start_date).label("yr"), func.count())
        .where(Project.tenant_id == tenant_id, Project.start_date.isnot(None))
        .group_by("yr")
        .order_by("yr")
    ).all()
    return [{"year": int(yr), "count": c} for yr, c in rows]
