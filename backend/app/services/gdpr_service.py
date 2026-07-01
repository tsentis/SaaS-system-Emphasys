"""GDPR data-subject requests: access (export) and erasure.

Operates on personal data (``persons``) keyed by email. Erasure anonymizes matching
records; access returns them. The session is tenant-bound, so a request only ever
touches the caller's tenant.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.governance import GdprRequest
from app.models.organization import Person

ACCESS = "access"
ERASURE = "erasure"
VALID_TYPES = {ACCESS, ERASURE}


def create_request(
    db: Session, *, tenant_id: uuid.UUID, subject_email: str, request_type: str
) -> GdprRequest:
    request = GdprRequest(
        tenant_id=tenant_id,
        subject_email=subject_email.lower(),
        request_type=request_type,
        status="pending",
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def list_requests(db: Session) -> list[GdprRequest]:
    return list(
        db.execute(
            select(GdprRequest).order_by(GdprRequest.created_at.desc())
        ).scalars()
    )


def get_request(db: Session, request_id: uuid.UUID) -> GdprRequest | None:
    return db.get(GdprRequest, request_id)


def _subjects(db: Session, email: str) -> list[Person]:
    return list(
        db.execute(select(Person).where(Person.email == email.lower())).scalars()
    )


def process(db: Session, request: GdprRequest) -> dict:
    persons = _subjects(db, request.subject_email)

    if request.request_type == ERASURE:
        for p in persons:
            p.email = None
            p.full_name = "[erased]"
            p.role = None
        result = {"action": "erasure", "erased_persons": len(persons)}
    else:  # access
        result = {
            "action": "access",
            "persons": [
                {"full_name": p.full_name, "email": p.email, "role": p.role}
                for p in persons
            ],
        }

    request.status = "completed"
    db.commit()
    return result
