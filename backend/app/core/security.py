"""Password hashing and JWT token issuance/verification (self-hosted auth).

This module is the only place that knows *how* identity is verified. Keeping it
isolated means a future swap to a managed provider (Clerk/SSO) touches just this file
plus the auth dependency.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

import bcrypt
import jwt

from app.core.config import settings

TokenType = Literal["access", "refresh"]


# --- Passwords ---

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


# --- JWT ---

def _create_token(
    *, user_id: uuid.UUID, tenant_id: uuid.UUID, token_type: TokenType, expires: timedelta
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    return _create_token(
        user_id=user_id,
        tenant_id=tenant_id,
        token_type="access",
        expires=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    return _create_token(
        user_id=user_id,
        tenant_id=tenant_id,
        token_type="refresh",
        expires=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str, expected_type: TokenType) -> dict:
    """Decode and validate a token, raising ``jwt.InvalidTokenError`` on any problem."""
    payload = jwt.decode(
        token, settings.secret_key, algorithms=[settings.jwt_algorithm]
    )
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"expected {expected_type} token")
    return payload
