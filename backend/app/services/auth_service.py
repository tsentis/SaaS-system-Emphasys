"""Authentication & registration business logic."""

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.roles import ADMIN
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.tenant import Tenant
from app.models.user import Role, User, UserRole


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"


def _unique_slug(db: Session, base: str) -> str:
    slug = base
    n = 1
    while db.execute(select(Tenant.id).where(Tenant.slug == slug)).first():
        n += 1
        slug = f"{base}-{n}"
    return slug


def _assign_role(db: Session, user_id: uuid.UUID, role_name: str) -> None:
    role_id = db.execute(select(Role.id).where(Role.name == role_name)).scalar_one()
    db.add(UserRole(user_id=user_id, role_id=role_id))


def register_tenant_and_admin(
    db: Session, *, organization_name: str, email: str, password: str, full_name: str | None
) -> tuple[Tenant, User]:
    """Create a new tenant and its first admin user. Raises ValueError on conflict."""
    slug = _unique_slug(db, _slugify(organization_name))

    tenant = Tenant(name=organization_name, slug=slug)
    db.add(tenant)
    db.flush()  # assigns tenant.id

    user = User(
        tenant_id=tenant.id,
        email=email.lower(),
        full_name=full_name,
        password_hash=hash_password(password),
        status="active",
    )
    db.add(user)
    db.flush()

    _assign_role(db, user.id, ADMIN)
    db.commit()
    db.refresh(tenant)
    db.refresh(user)
    return tenant, user


def authenticate(
    db: Session, *, tenant_slug: str, email: str, password: str
) -> User | None:
    """Return the user if credentials are valid, else None."""
    tenant_id = db.execute(
        select(Tenant.id).where(Tenant.slug == tenant_slug, Tenant.is_active.is_(True))
    ).scalar_one_or_none()
    if tenant_id is None:
        return None

    user = db.execute(
        select(User).where(
            User.tenant_id == tenant_id, func.lower(User.email) == email.lower()
        )
    ).scalar_one_or_none()
    if user is None or user.status != "active":
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def issue_tokens(user: User) -> tuple[str, str]:
    return (
        create_access_token(user.id, user.tenant_id),
        create_refresh_token(user.id, user.tenant_id),
    )
