"""User management schemas (admin-facing)."""

import uuid

from pydantic import BaseModel, EmailStr, Field

from app.core.roles import ALL_ROLES


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    status: str
    roles: list[str]


class UserCreate(BaseModel):
    """Admin creates a user within their tenant."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)
    role: str = Field(default="viewer")

    def validate_role(self) -> str:
        if self.role not in ALL_ROLES:
            raise ValueError(f"role must be one of {ALL_ROLES}")
        return self.role


class RoleAssignment(BaseModel):
    role: str

    def validate_role(self) -> str:
        if self.role not in ALL_ROLES:
            raise ValueError(f"role must be one of {ALL_ROLES}")
        return self.role
