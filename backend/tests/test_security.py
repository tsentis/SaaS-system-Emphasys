"""Unit tests for password hashing and JWT handling (no database required)."""

import uuid

import jwt
import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("s3cret-password")
    assert hashed != "s3cret-password"
    assert verify_password("s3cret-password", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip() -> None:
    uid, tid = uuid.uuid4(), uuid.uuid4()
    token = create_access_token(uid, tid)
    claims = decode_token(token, expected_type="access")
    assert claims["sub"] == str(uid)
    assert claims["tid"] == str(tid)
    assert claims["type"] == "access"


def test_token_type_is_enforced() -> None:
    token = create_refresh_token(uuid.uuid4(), uuid.uuid4())
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(token, expected_type="access")


def test_tampered_token_rejected() -> None:
    token = create_access_token(uuid.uuid4(), uuid.uuid4())
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(token + "x", expected_type="access")
