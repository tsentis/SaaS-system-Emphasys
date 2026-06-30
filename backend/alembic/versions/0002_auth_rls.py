"""auth: password column, seed roles, row-level security

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-30

Adds the self-hosted-auth password column, seeds the RBAC role catalogue, and enables
PostgreSQL Row-Level Security on every tenant-scoped table.

Note on RLS: policies compare ``tenant_id`` against the ``app.current_tenant`` GUC set
by the application per request. ``FORCE ROW LEVEL SECURITY`` makes the table owner
subject to them too — but PostgreSQL *superusers* always bypass RLS. To get database-
level enforcement in production, connect the application as a dedicated non-superuser
role (see README). In development (superuser connection) the application-layer query
guard provides isolation; these policies are defense in depth.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables carrying a tenant_id column.
TENANT_TABLES = [
    "users",
    "documents",
    "analysis_runs",
    "organizations",
    "persons",
    "projects",
    "project_partners",
    "work_packages",
    "external_enrichment",
    "embeddings",
    "audit_log",
    "gdpr_requests",
    "api_keys",
]

ROLES = [
    ("11111111-1111-1111-1111-111111111111", "admin", "Full tenant administration"),
    ("22222222-2222-2222-2222-222222222222", "analyst", "Upload and analyze proposals"),
    ("33333333-3333-3333-3333-333333333333", "viewer", "Read-only access"),
]


def upgrade() -> None:
    # 1) password column for self-hosted auth
    op.add_column("users", sa.Column("password_hash", sa.String(), nullable=True))

    # 2) seed RBAC roles
    roles_table = sa.table(
        "roles",
        sa.column("id", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
    )
    op.bulk_insert(
        roles_table,
        [{"id": rid, "name": name, "description": desc} for rid, name, desc in ROLES],
    )

    # 3) Row-Level Security on tenant-scoped tables
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant', true)::uuid)
            """
        )


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.execute(
        "DELETE FROM roles WHERE name IN ('admin', 'analyst', 'viewer')"
    )
    op.drop_column("users", "password_hash")
