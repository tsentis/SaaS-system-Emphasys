"""Append-only audit logging (GDPR / security)."""

import uuid

from sqlalchemy.orm import Session

from app.models.governance import AuditLog


def record(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID | None,
    action: str,
    entity: str | None = None,
    entity_id: uuid.UUID | None = None,
    ip_address: str | None = None,
) -> None:
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            ip_address=ip_address,
        )
    )
    db.commit()
