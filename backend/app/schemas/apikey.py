"""API key schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scopes: str | None = Field(default=None, description="comma-separated scopes")


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    scopes: str | None
    is_active: bool
    last_used_at: str | None
    created_at: datetime


class ApiKeyCreated(ApiKeyOut):
    # The raw key, shown only once at creation.
    key: str
