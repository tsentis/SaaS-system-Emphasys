"""Test fixtures.

Integration tests need a real PostgreSQL (the models use UUID/JSONB/pgvector types).
Point them at a disposable database via the ``TEST_DATABASE_URL`` env var, e.g.:

    TEST_DATABASE_URL=postgresql+psycopg://emphasys:change-me-in-prod@localhost:5432/emphasys_test

If it is unset or unreachable, the integration tests are skipped. Pure unit tests
(e.g. ``test_security.py``) have no database dependency and always run.
"""

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

ROLE_IDS = {
    "admin": "11111111-1111-1111-1111-111111111111",
    "analyst": "22222222-2222-2222-2222-222222222222",
    "viewer": "33333333-3333-3333-3333-333333333333",
}


@pytest.fixture(scope="session")
def engine():
    """Session-scoped engine against the test DB; skips if unavailable."""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set; skipping DB integration tests")
    eng = create_engine(TEST_DATABASE_URL, future=True)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Test database unreachable: {exc}")

    from app.models import Base  # imported lazily so the skip happens first

    with eng.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def client(engine):
    """TestClient using the test DB. Seeds RBAC roles, wipes tenant data afterwards."""
    from fastapi.testclient import TestClient

    from app.core.db import get_db
    from app.main import app

    TestSession = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False, future=True
    )

    with TestSession() as s:
        for name, rid in ROLE_IDS.items():
            s.execute(
                text(
                    "INSERT INTO roles (id, name, description) "
                    "VALUES (:id, :name, :name) ON CONFLICT (name) DO NOTHING"
                ),
                {"id": rid, "name": name},
            )
        s.commit()

    def _override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

    with engine.begin() as conn:
        for table in ("user_roles", "users", "tenants"):
            conn.execute(text(f"DELETE FROM {table}"))
