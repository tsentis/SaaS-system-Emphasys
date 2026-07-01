"""Partner organization resolution / deduplication.

A ``normalized_key`` collapses spelling variants of the same organization so the same
partner isn't stored twice. Milestone 3 does exact normalized-key (and PIC) matching;
Milestone 4 layers fuzzy matching on top.
"""

import re
import uuid
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization

# Names whose normalized keys are at least this similar are treated as the same org.
FUZZY_THRESHOLD = 0.9

_LEGAL_SUFFIXES = {
    "ltd", "limited", "gmbh", "srl", "spa", "sa", "sas", "bv", "nv", "oy", "ab",
    "as", "plc", "llc", "inc", "co", "eood", "ood", "sl", "sro", "kft", "doo",
    "university", "univ", "foundation", "association", "asbl", "ev",
}


def normalize_key(name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", name.lower())
    tokens = [t for t in cleaned.split() if t and t not in _LEGAL_SUFFIXES]
    return " ".join(tokens) or name.lower().strip()


def resolve_organization(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    legal_name: str,
    country: str | None = None,
    org_type: str | None = None,
    pic_number: str | None = None,
) -> Organization:
    """Find an existing matching organization in the tenant, or create one."""
    if pic_number:
        existing = db.execute(
            select(Organization).where(Organization.pic_number == pic_number)
        ).scalar_one_or_none()
        if existing:
            return existing

    key = normalize_key(legal_name)
    existing = db.execute(
        select(Organization).where(Organization.normalized_key == key)
    ).scalar_one_or_none()
    if existing:
        return existing

    fuzzy = _best_fuzzy_match(db, key)
    if fuzzy is not None:
        return fuzzy

    org = Organization(
        tenant_id=tenant_id,
        legal_name=legal_name,
        normalized_key=key,
        country=country,
        org_type=org_type,
        pic_number=pic_number,
    )
    db.add(org)
    db.flush()
    return org


def _best_fuzzy_match(db: Session, key: str) -> Organization | None:
    """Return the tenant org whose normalized_key is most similar to ``key``,
    if the similarity meets the threshold. Session is already tenant-scoped."""
    best: Organization | None = None
    best_ratio = 0.0
    for org in db.execute(select(Organization)).scalars():
        ratio = SequenceMatcher(None, key, org.normalized_key).ratio()
        if ratio > best_ratio:
            best, best_ratio = org, ratio
    return best if best_ratio >= FUZZY_THRESHOLD else None
