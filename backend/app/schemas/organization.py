"""Organization registry schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    legal_name: str
    country: str | None
    org_type: str | None
    pic_number: str | None
    website: str | None
    created_at: datetime


class OrgProjectRef(BaseModel):
    project_id: uuid.UUID
    acronym: str | None
    title: str | None
    role: str | None


class OrganizationDetail(OrganizationOut):
    projects: list[OrgProjectRef] = []


class OrganizationUpdate(BaseModel):
    legal_name: str | None = None
    country: str | None = None
    org_type: str | None = None
    website: str | None = None
    pic_number: str | None = None


class MergeRequest(BaseModel):
    duplicate_id: uuid.UUID
