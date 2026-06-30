"""Document schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    mime_type: str | None
    page_count: int | None
    size_bytes: int | None
    sha256: str | None
    status: str
    created_at: datetime


class UploadResult(BaseModel):
    document: DocumentOut
    # True when an identical file (same SHA-256) already existed in the tenant.
    duplicate: bool


class DownloadUrl(BaseModel):
    url: str
    expires_in: int
