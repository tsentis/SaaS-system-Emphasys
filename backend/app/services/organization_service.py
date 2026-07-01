"""Organization registry: querying, editing, and merging duplicate partners."""

import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models.organization import Organization, Person
from app.models.project import Project, ProjectPartner, WorkPackage
from app.services.org_resolution import normalize_key


def list_organizations(
    db: Session,
    *,
    country: str | None = None,
    org_type: str | None = None,
    q: str | None = None,
) -> list[Organization]:
    stmt = select(Organization)
    if country:
        stmt = stmt.where(Organization.country == country)
    if org_type:
        stmt = stmt.where(Organization.org_type == org_type)
    if q:
        stmt = stmt.where(Organization.legal_name.ilike(f"%{q}%"))
    return list(db.execute(stmt.order_by(Organization.legal_name)).scalars())


def get_organization(db: Session, org_id: uuid.UUID) -> Organization | None:
    return db.get(Organization, org_id)


def projects_for(db: Session, org_id: uuid.UUID) -> list[tuple[Project, str | None]]:
    rows = db.execute(
        select(Project, ProjectPartner.role)
        .join(ProjectPartner, ProjectPartner.project_id == Project.id)
        .where(ProjectPartner.organization_id == org_id)
        .order_by(Project.created_at.desc())
    ).all()
    return [(p, role) for p, role in rows]


def update_organization(db: Session, org: Organization, data: dict) -> Organization:
    for field in ("legal_name", "country", "org_type", "website", "pic_number"):
        if field in data and data[field] is not None:
            setattr(org, field, data[field])
    if "legal_name" in data and data["legal_name"]:
        org.normalized_key = normalize_key(data["legal_name"])
    db.commit()
    db.refresh(org)
    return org


def merge(db: Session, keep: Organization, duplicate: Organization) -> Organization:
    """Merge ``duplicate`` into ``keep``: reassign links, then delete the duplicate."""
    # Projects already linked to keep — drop the duplicate's link to avoid collisions.
    keep_project_ids = set(
        db.execute(
            select(ProjectPartner.project_id).where(
                ProjectPartner.organization_id == keep.id
            )
        ).scalars()
    )
    if keep_project_ids:
        db.execute(
            delete(ProjectPartner).where(
                ProjectPartner.organization_id == duplicate.id,
                ProjectPartner.project_id.in_(keep_project_ids),
            )
        )
    db.execute(
        update(ProjectPartner)
        .where(ProjectPartner.organization_id == duplicate.id)
        .values(organization_id=keep.id)
    )
    db.execute(
        update(WorkPackage)
        .where(WorkPackage.lead_organization_id == duplicate.id)
        .values(lead_organization_id=keep.id)
    )
    db.execute(
        update(Person)
        .where(Person.organization_id == duplicate.id)
        .values(organization_id=keep.id)
    )
    db.execute(delete(Organization).where(Organization.id == duplicate.id))
    db.commit()
    db.refresh(keep)
    return keep


def count(db: Session) -> int:
    return db.execute(select(func.count()).select_from(Organization)).scalar_one()
