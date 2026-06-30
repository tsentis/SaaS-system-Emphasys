"""Database engine, session factory, and tenant isolation.

Two layers of tenant isolation:

1. **Application layer (always on).** A ``do_orm_execute`` event injects a
   ``tenant_id`` filter into every ORM query against a :class:`TenantScoped` model,
   based on the tenant bound to the session. This works regardless of the database
   role and is what the test-suite exercises.
2. **Database layer (defense in depth).** ``set_tenant`` sets the ``app.current_tenant``
   GUC so PostgreSQL Row-Level Security policies (migration 0002) enforce isolation
   too — effective when the app connects as a non-superuser role (see README).
"""

import uuid
from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker, with_loader_criteria

from app.core.config import settings
from app.models.base import TenantScoped

engine = create_engine(settings.sqlalchemy_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# Key under which the active tenant is stored on ``session.info``.
TENANT_KEY = "tenant_id"


def bind_tenant(session: Session, tenant_id: uuid.UUID) -> None:
    """Bind a tenant to a session: app-layer filter + database RLS GUC."""
    session.info[TENANT_KEY] = tenant_id
    set_tenant(session, tenant_id)


def set_tenant(session: Session, tenant_id: uuid.UUID) -> None:
    """Set the Postgres GUC that RLS policies read."""
    session.execute(
        text("SELECT set_config('app.current_tenant', :tid, true)"),
        {"tid": str(tenant_id)},
    )


@event.listens_for(Session, "do_orm_execute")
def _apply_tenant_filter(orm_execute_state) -> None:
    """Auto-filter every SELECT on a TenantScoped entity by the session's tenant."""
    if not orm_execute_state.is_select:
        return
    session = orm_execute_state.session
    tenant_id = session.info.get(TENANT_KEY)
    if tenant_id is None:
        return
    orm_execute_state.statement = orm_execute_state.statement.options(
        with_loader_criteria(
            TenantScoped,
            lambda cls: cls.tenant_id == tenant_id,
            include_aliases=True,
        )
    )


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a (tenant-unbound) database session.

    The auth dependency binds the tenant once the request is authenticated.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
