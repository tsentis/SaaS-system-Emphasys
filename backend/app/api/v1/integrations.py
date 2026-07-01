"""Public integration API — authenticated by API key (X-API-Key)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import ApiPrincipal, get_api_principal
from app.schemas.organization import OrganizationOut
from app.schemas.project import ProjectOut
from app.services import organization_service, project_service

router = APIRouter(tags=["integrations"])


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(
    db: Session = Depends(get_db),
    _: ApiPrincipal = Depends(get_api_principal),
) -> list[ProjectOut]:
    return [ProjectOut.model_validate(p) for p in project_service.list_projects(db)]


@router.get("/organizations", response_model=list[OrganizationOut])
def list_organizations(
    db: Session = Depends(get_db),
    _: ApiPrincipal = Depends(get_api_principal),
) -> list[OrganizationOut]:
    orgs = organization_service.list_organizations(db)
    return [OrganizationOut.model_validate(o) for o in orgs]
