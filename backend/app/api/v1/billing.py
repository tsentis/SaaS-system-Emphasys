"""Billing / plan endpoints (admin)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_roles
from app.core.roles import ADMIN
from app.schemas.governance import PlanOut, PlanUpdate
from app.services import billing_service

router = APIRouter(tags=["billing"])


@router.get("/plan", response_model=PlanOut)
def get_plan(
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_roles(ADMIN)),
) -> PlanOut:
    return PlanOut(plan=billing_service.get_plan(db, current.tenant_id))


@router.put("/plan", response_model=PlanOut)
def set_plan(
    payload: PlanUpdate,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_roles(ADMIN)),
) -> PlanOut:
    try:
        plan = billing_service.set_plan(
            db,
            billing_service.get_provider(),
            tenant_id=current.tenant_id,
            plan=payload.plan,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None
    return PlanOut(plan=plan)
