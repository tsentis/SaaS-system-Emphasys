"""API key management for machine-to-machine access.

Keys are stored only as SHA-256 hashes; the raw key is returned once at creation.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import generate_api_key, hash_api_key
from app.models.governance import ApiKey


def create_key(
    db: Session, *, tenant_id: uuid.UUID, name: str, scopes: str | None = None
) -> tuple[ApiKey, str]:
    raw, hashed = generate_api_key()
    key = ApiKey(tenant_id=tenant_id, name=name, hashed_key=hashed, scopes=scopes)
    db.add(key)
    db.commit()
    db.refresh(key)
    return key, raw


def list_keys(db: Session) -> list[ApiKey]:
    return list(
        db.execute(select(ApiKey).order_by(ApiKey.created_at.desc())).scalars()
    )


def get_key(db: Session, key_id: uuid.UUID) -> ApiKey | None:
    return db.get(ApiKey, key_id)


def revoke(db: Session, key: ApiKey) -> None:
    key.is_active = False
    db.commit()


def authenticate(db: Session, raw: str) -> ApiKey | None:
    """Look up an active key by its raw value. Session should be unbound so the
    lookup can find the key across tenants before the tenant is known."""
    return db.execute(
        select(ApiKey).where(
            ApiKey.hashed_key == hash_api_key(raw), ApiKey.is_active.is_(True)
        )
    ).scalar_one_or_none()


def touch(db: Session, key: ApiKey) -> None:
    key.last_used_at = datetime.now(UTC).isoformat()
    db.commit()
