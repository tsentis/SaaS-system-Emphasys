"""Database engine, session factory, and FastAPI dependency.

Multi-tenancy note: PostgreSQL Row-Level Security policies (added in Milestone 1)
read the current tenant from the ``app.current_tenant`` session setting. The
``set_tenant`` helper sets it on a connection; the request middleware will call it
once authentication is in place.
"""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.sqlalchemy_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def set_tenant(session: Session, tenant_id: str) -> None:
    """Bind the active tenant for RLS on this session's connection."""
    session.execute(
        text("SELECT set_config('app.current_tenant', :tid, true)"),
        {"tid": str(tenant_id)},
    )


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
