"""GDPR data-subject request endpoints (admin)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_roles
from app.core.roles import ADMIN
from app.schemas.governance import GdprRequestCreate, GdprRequestOut
from app.services import gdpr_service

router = APIRouter(tags=["gdpr"])


@router.post("/requests", response_model=GdprRequestOut, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: GdprRequestCreate,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_roles(ADMIN)),
) -> GdprRequestOut:
    if payload.request_type not in gdpr_service.VALID_TYPES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"request_type must be one of {sorted(gdpr_service.VALID_TYPES)}",
        )
    req = gdpr_service.create_request(
        db,
        tenant_id=current.tenant_id,
        subject_email=payload.subject_email,
        request_type=payload.request_type,
    )
    return GdprRequestOut.model_validate(req)


@router.get("/requests", response_model=list[GdprRequestOut])
def list_requests(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ADMIN)),
) -> list[GdprRequestOut]:
    return [GdprRequestOut.model_validate(r) for r in gdpr_service.list_requests(db)]


@router.post("/requests/{request_id}/process")
def process_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ADMIN)),
) -> dict:
    req = gdpr_service.get_request(db, request_id)
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    return gdpr_service.process(db, req)
