"""API key management (admin, JWT-authenticated)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_roles
from app.core.roles import ADMIN
from app.schemas.apikey import ApiKeyCreate, ApiKeyCreated, ApiKeyOut
from app.services import apikey_service

router = APIRouter(tags=["api-keys"])


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
def create_key(
    payload: ApiKeyCreate,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_roles(ADMIN)),
) -> ApiKeyCreated:
    key, raw = apikey_service.create_key(
        db, tenant_id=current.tenant_id, name=payload.name, scopes=payload.scopes
    )
    return ApiKeyCreated(**ApiKeyOut.model_validate(key).model_dump(), key=raw)


@router.get("", response_model=list[ApiKeyOut])
def list_keys(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ADMIN)),
) -> list[ApiKeyOut]:
    return [ApiKeyOut.model_validate(k) for k in apikey_service.list_keys(db)]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_key(
    key_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ADMIN)),
) -> None:
    key = apikey_service.get_key(db, key_id)
    if key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    apikey_service.revoke(db, key)
