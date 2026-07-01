"""Search across projects: keyword + faceted filters, and pgvector semantic search."""

import uuid
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ai.embedder import Embedder
from app.models.enrichment import Embedding
from app.models.organization import Organization
from app.models.programme import Programme
from app.models.project import Project, ProjectPartner


def search_projects(
    db: Session,
    *,
    q: str | None = None,
    programme: str | None = None,
    country: str | None = None,
    status: str | None = None,
    min_budget: float | None = None,
    max_budget: float | None = None,
    starts_after: date | None = None,
    ends_before: date | None = None,
) -> list[Project]:
    stmt = select(Project)

    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Project.title.ilike(like),
                Project.acronym.ilike(like),
                Project.summary.ilike(like),
            )
        )
    if programme:
        stmt = stmt.join(Programme, Programme.id == Project.programme_id).where(
            Programme.name.ilike(f"%{programme}%")
        )
    if country:
        stmt = (
            stmt.join(ProjectPartner, ProjectPartner.project_id == Project.id)
            .join(Organization, Organization.id == ProjectPartner.organization_id)
            .where(Organization.country == country)
        )
    if status:
        stmt = stmt.where(Project.status == status)
    if min_budget is not None:
        stmt = stmt.where(Project.total_budget >= min_budget)
    if max_budget is not None:
        stmt = stmt.where(Project.total_budget <= max_budget)
    if starts_after is not None:
        stmt = stmt.where(Project.start_date >= starts_after)
    if ends_before is not None:
        stmt = stmt.where(Project.end_date <= ends_before)

    stmt = stmt.distinct().order_by(Project.created_at.desc())
    return list(db.execute(stmt).scalars())


def semantic_search(
    db: Session, embedder: Embedder, *, q: str, limit: int = 10
) -> list[Project]:
    """Nearest projects to the query text by embedding cosine distance."""
    query_vec = embedder.embed(q)
    rows = db.execute(
        select(Project)
        .join(Embedding, Embedding.owner_id == Project.id)
        .where(Embedding.owner_type == "project")
        .order_by(Embedding.vector.cosine_distance(query_vec))
        .limit(limit)
    ).scalars()
    return list(rows)
