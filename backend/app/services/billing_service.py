"""Billing scaffold.

A ``BillingProvider`` abstracts the payment backend (Stripe in production). The default
``NoopBillingProvider`` records plan changes locally without charging — enough for
internal use; a real provider is dropped in later.
"""

import uuid
from typing import Protocol

from sqlalchemy.orm import Session

from app.models.tenant import Tenant

PLANS = ("free", "pro", "enterprise")


class BillingProvider(Protocol):
    def change_plan(self, *, tenant_id: uuid.UUID, plan: str) -> None: ...


class NoopBillingProvider:
    def change_plan(self, *, tenant_id: uuid.UUID, plan: str) -> None:
        return None


def get_provider() -> BillingProvider:
    return NoopBillingProvider()


def get_plan(db: Session, tenant_id: uuid.UUID) -> str:
    tenant = db.get(Tenant, tenant_id)
    return tenant.plan if tenant else "free"


def set_plan(
    db: Session, provider: BillingProvider, *, tenant_id: uuid.UUID, plan: str
) -> str:
    if plan not in PLANS:
        raise ValueError(f"plan must be one of {PLANS}")
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("tenant not found")
    provider.change_plan(tenant_id=tenant_id, plan=plan)
    tenant.plan = plan
    db.commit()
    return plan
