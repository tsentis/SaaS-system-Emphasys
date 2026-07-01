"""Partner organization registry endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user, require_roles
from app.core.roles import ADMIN, ANALYST
from app.schemas.organization import (
    MergeRequest,
    OrganizationDetail,
    OrganizationOut,
    OrganizationUpdate,
    OrgProjectRef,
)
from app.services import organization_service

router = APIRouter(tags=["organizations"])


def _detail(db: Session, org) -> OrganizationDetail:
    projects = [
        OrgProjectRef(
            project_id=p.id, acronym=p.acronym, title=p.title, role=role
        )
        for p, role in organization_service.projects_for(db, org.id)
    ]
    detail = OrganizationDetail.model_validate(org)
    detail.projects = projects
    return detail


@router.get("", response_model=list[OrganizationOut])
def list_organizations(
    country: str | None = None,
    org_type: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> list[OrganizationOut]:
    orgs = organization_service.list_organizations(
        db, country=country, org_type=org_type, q=q
    )
    return [OrganizationOut.model_validate(o) for o in orgs]


@router.get("/{org_id}", response_model=OrganizationDetail)
def get_organization(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> OrganizationDetail:
    org = organization_service.get_organization(db, org_id)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    return _detail(db, org)


@router.patch("/{org_id}", response_model=OrganizationDetail)
def update_organization(
    org_id: uuid.UUID,
    payload: OrganizationUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ADMIN, ANALYST)),
) -> OrganizationDetail:
    org = organization_service.get_organization(db, org_id)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    org = organization_service.update_organization(
        db, org, payload.model_dump(exclude_unset=True)
    )
    return _detail(db, org)


@router.post("/{org_id}/merge", response_model=OrganizationDetail)
def merge_organizations(
    org_id: uuid.UUID,
    payload: MergeRequest,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ADMIN)),
) -> OrganizationDetail:
    if payload.duplicate_id == org_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot merge an org into itself")
    keep = organization_service.get_organization(db, org_id)
    duplicate = organization_service.get_organization(db, payload.duplicate_id)
    if keep is None or duplicate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    keep = organization_service.merge(db, keep, duplicate)
    return _detail(db, keep)
