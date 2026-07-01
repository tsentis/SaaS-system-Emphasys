"""Project persistence and queries."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.schemas import ExtractedProject
from app.models.organization import Organization
from app.models.programme import Programme
from app.models.project import Project, ProjectPartner
from app.services import org_resolution


def get_or_create_programme(db: Session, name: str | None) -> Programme | None:
    if not name:
        return None
    existing = db.execute(
        select(Programme).where(func.lower(Programme.name) == name.lower())
    ).scalar_one_or_none()
    if existing:
        return existing
    programme = Programme(name=name)
    db.add(programme)
    db.flush()
    return programme


def persist_extraction(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    document_id: uuid.UUID,
    extracted: ExtractedProject,
) -> Project:
    """Create a Project plus resolved partner organizations from an extraction."""
    programme = get_or_create_programme(db, extracted.programme)

    project = Project(
        tenant_id=tenant_id,
        document_id=document_id,
        programme_id=programme.id if programme else None,
        acronym=extracted.acronym,
        title=extracted.title,
        summary=extracted.summary,
        total_budget=extracted.total_budget,
        start_date=extracted.start_date,
        end_date=extracted.end_date,
        status="extracted",
        extraction_confidence=extracted.confidence,
    )
    db.add(project)
    db.flush()

    for partner in extracted.partners:
        org = org_resolution.resolve_organization(
            db,
            tenant_id=tenant_id,
            legal_name=partner.legal_name,
            country=partner.country,
            org_type=partner.org_type,
            pic_number=partner.pic_number,
        )
        db.add(
            ProjectPartner(
                tenant_id=tenant_id,
                project_id=project.id,
                organization_id=org.id,
                role=partner.role,
            )
        )

    db.flush()
    return project


def list_projects(db: Session) -> list[Project]:
    return list(
        db.execute(select(Project).order_by(Project.created_at.desc())).scalars()
    )


def get_project(db: Session, project_id: uuid.UUID) -> Project | None:
    return db.get(Project, project_id)


def partners_of(db: Session, project_id: uuid.UUID) -> list[ProjectPartner]:
    return list(
        db.execute(
            select(ProjectPartner).where(ProjectPartner.project_id == project_id)
        ).scalars()
    )


def partners_with_orgs(
    db: Session, project_id: uuid.UUID
) -> list[tuple[ProjectPartner, Organization]]:
    return list(
        db.execute(
            select(ProjectPartner, Organization)
            .join(Organization, Organization.id == ProjectPartner.organization_id)
            .where(ProjectPartner.project_id == project_id)
        ).all()
    )
