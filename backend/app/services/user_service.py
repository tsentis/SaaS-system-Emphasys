"""User management within a tenant (admin operations).

All queries run on a tenant-bound session, so the ``do_orm_execute`` guard scopes
them to the caller's tenant automatically.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import Role, User, UserRole


def list_users(db: Session) -> list[User]:
    return list(db.execute(select(User).order_by(User.created_at)).scalars())


def get_user(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def roles_for(db: Session, user_id: uuid.UUID) -> list[str]:
    return list(
        db.execute(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        ).scalars()
    )


def email_exists(db: Session, email: str) -> bool:
    return (
        db.execute(select(User.id).where(User.email == email.lower())).first()
        is not None
    )


def create_user(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    email: str,
    password: str,
    full_name: str | None,
    role: str,
) -> User:
    user = User(
        tenant_id=tenant_id,
        email=email.lower(),
        full_name=full_name,
        password_hash=hash_password(password),
        status="active",
    )
    db.add(user)
    db.flush()
    assign_role(db, user.id, role)
    db.commit()
    db.refresh(user)
    return user


def assign_role(db: Session, user_id: uuid.UUID, role_name: str) -> None:
    role_id = db.execute(select(Role.id).where(Role.name == role_name)).scalar_one()
    exists = db.execute(
        select(UserRole).where(
            UserRole.user_id == user_id, UserRole.role_id == role_id
        )
    ).first()
    if not exists:
        db.add(UserRole(user_id=user_id, role_id=role_id))
        db.commit()


def set_status(db: Session, user: User, status: str) -> User:
    user.status = status
    db.commit()
    db.refresh(user)
    return user
