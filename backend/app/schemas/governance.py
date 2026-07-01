"""GDPR, audit, and billing schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class GdprRequestCreate(BaseModel):
    subject_email: EmailStr
    request_type: str  # access | erasure


class GdprRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_email: str
    request_type: str
    status: str
    created_at: datetime


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action: str
    entity: str | None
    entity_id: uuid.UUID | None
    user_id: uuid.UUID | None
    ip_address: str | None
    created_at: datetime


class PlanOut(BaseModel):
    plan: str


class PlanUpdate(BaseModel):
    plan: str
