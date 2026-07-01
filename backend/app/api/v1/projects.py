"""Project extraction and retrieval endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.ai.extractor import Extractor, get_extractor
from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user, require_roles
from app.core.roles import ADMIN, ANALYST
from app.core.storage import Storage, get_storage
from app.schemas.project import PartnerOut, ProjectDetail, ProjectOut
from app.services import audit_service, document_service, extraction_service, project_service

router = APIRouter(tags=["projects"])


def _detail(db: Session, project) -> ProjectDetail:
    partners = [
        PartnerOut(
            organization_id=org.id,
            legal_name=org.legal_name,
            country=org.country,
            org_type=org.org_type,
            role=pp.role,
        )
        for pp, org in project_service.partners_with_orgs(db, project.id)
    ]
    detail = ProjectDetail.model_validate(project)
    detail.partners = partners
    return detail


@router.post(
    "/from-document/{document_id}",
    response_model=ProjectDetail,
    status_code=status.HTTP_201_CREATED,
)
def analyze_document(
    document_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    extractor: Extractor = Depends(get_extractor),
    current: CurrentUser = Depends(require_roles(ADMIN, ANALYST)),
) -> ProjectDetail:
    document = document_service.get_document(db, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    project = extraction_service.analyze_document(
        db, storage, extractor, document=document
    )
    audit_service.record(
        db,
        tenant_id=current.tenant_id,
        user_id=current.id,
        action="document.analyze",
        entity="project",
        entity_id=project.id,
        ip_address=request.client.host if request.client else None,
    )
    return _detail(db, project)


@router.get("", response_model=list[ProjectOut])
def list_projects(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> list[ProjectOut]:
    return [ProjectOut.model_validate(p) for p in project_service.list_projects(db)]


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> ProjectDetail:
    project = project_service.get_project(db, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return _detail(db, project)
