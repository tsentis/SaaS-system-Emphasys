"""Tenant user management (admin only)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_roles
from app.core.db import get_db
from app.core.roles import ADMIN
from app.schemas.user import RoleAssignment, UserCreate, UserOut
from app.services import user_service

router = APIRouter(tags=["users"])


def _to_out(db: Session, user) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        status=user.status,
        roles=user_service.roles_for(db, user.id),
    )


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ADMIN)),
) -> list[UserOut]:
    return [_to_out(db, u) for u in user_service.list_users(db)]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_roles(ADMIN)),
) -> UserOut:
    try:
        role = payload.validate_role()
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None
    if user_service.email_exists(db, payload.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already in use")
    user = user_service.create_user(
        db,
        tenant_id=current.tenant_id,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        role=role,
    )
    return _to_out(db, user)


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ADMIN)),
) -> UserOut:
    user = user_service.get_user(db, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return _to_out(db, user)


@router.post("/{user_id}/roles", response_model=UserOut)
def assign_role(
    user_id: uuid.UUID,
    payload: RoleAssignment,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ADMIN)),
) -> UserOut:
    try:
        role = payload.validate_role()
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None
    user = user_service.get_user(db, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user_service.assign_role(db, user.id, role)
    return _to_out(db, user)


@router.post("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_roles(ADMIN)),
) -> UserOut:
    user = user_service.get_user(db, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == current.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot deactivate yourself")
    return _to_out(db, user_service.set_status(db, user, "disabled"))
