"""Project & partner API schemas."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PartnerOut(BaseModel):
    organization_id: uuid.UUID
    legal_name: str
    country: str | None
    org_type: str | None
    role: str | None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID | None
    acronym: str | None
    title: str | None
    summary: str | None
    total_budget: float | None
    start_date: date | None
    end_date: date | None
    status: str
    extraction_confidence: float | None
    created_at: datetime


class ProjectDetail(ProjectOut):
    partners: list[PartnerOut] = []
