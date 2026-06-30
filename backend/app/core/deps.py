"""Shared FastAPI dependencies: authentication, tenant binding, and RBAC."""

import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import bind_tenant, get_db
from app.core.security import decode_token
from app.models.user import Role, User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


@dataclass
class CurrentUser:
    """The authenticated principal for a request."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    full_name: str | None
    roles: set[str]

    def has_role(self, *names: str) -> bool:
        return bool(self.roles.intersection(names))


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """Validate the bearer token, bind the tenant to the session, and load the user.

    Binding the tenant *before* loading the user means even this lookup is subject to
    tenant isolation.
    """
    if credentials is None:
        raise _CREDENTIALS_EXC
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        user_id = uuid.UUID(payload["sub"])
        tenant_id = uuid.UUID(payload["tid"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise _CREDENTIALS_EXC from None

    bind_tenant(db, tenant_id)

    user = db.get(User, user_id)
    if user is None or user.status != "active" or user.tenant_id != tenant_id:
        raise _CREDENTIALS_EXC

    role_names = set(
        db.execute(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id)
        ).scalars()
    )
    return CurrentUser(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        full_name=user.full_name,
        roles=role_names,
    )


def require_roles(*allowed: str):
    """Dependency factory: require the current user to hold one of ``allowed`` roles."""

    def _checker(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not current.has_role(*allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current

    return _checker
