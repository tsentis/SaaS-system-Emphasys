"""Audit log viewer (admin)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_roles
from app.core.roles import ADMIN
from app.schemas.governance import AuditOut
from app.services import audit_service

router = APIRouter(tags=["audit"])


@router.get("", response_model=list[AuditOut])
def list_audit(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ADMIN)),
) -> list[AuditOut]:
    return [AuditOut.model_validate(a) for a in audit_service.list_recent(db, limit)]
