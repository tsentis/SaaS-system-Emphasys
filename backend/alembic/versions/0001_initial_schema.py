"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-30

Creates the full normalized, multi-tenant schema for Milestone 0. Row-Level Security
policies are layered on in Milestone 1 once authentication sets the tenant context.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)
NOW = sa.text("now()")


def _ts_cols() -> list[sa.Column]:
    return [
        sa.Column("created_at", TS, server_default=NOW, nullable=False),
        sa.Column("updated_at", TS, server_default=NOW, nullable=False),
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- tenants ---
    op.create_table(
        "tenants",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False, unique=True),
        sa.Column("plan", sa.String(), nullable=False, server_default="free"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_ts_cols(),
    )

    # --- roles (system-wide catalogue) ---
    op.create_table(
        "roles",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("description", sa.String(), nullable=True),
    )

    # --- programmes (shared reference) ---
    op.create_table(
        "programmes",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("code", sa.String(), nullable=True, unique=True),
        *_ts_cols(),
    )

    # --- funding_calls ---
    op.create_table(
        "funding_calls",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "programme_id",
            UUID,
            sa.ForeignKey("programmes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("identifier", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("total_budget", sa.Numeric(18, 2), nullable=True),
        *_ts_cols(),
    )
    op.create_index("ix_funding_calls_programme_id", "funding_calls", ["programme_id"])
    op.create_index("ix_funding_calls_identifier", "funding_calls", ["identifier"])

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id",
            UUID,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("auth_provider_id", sa.String(), nullable=True, unique=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        *_ts_cols(),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_auth_provider_id", "users", ["auth_provider_id"])

    # --- user_roles ---
    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "role_id",
            UUID,
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    # --- documents ---
    op.create_table(
        "documents",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id",
            UUID,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("s3_key", sa.String(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=True),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="uploaded"),
        sa.Column(
            "uploaded_by",
            UUID,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        *_ts_cols(),
    )
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"])
    op.create_index("ix_documents_sha256", "documents", ["sha256"])
    op.create_index("ix_documents_status", "documents", ["status"])

    # --- analysis_runs ---
    op.create_table(
        "analysis_runs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id",
            UUID,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            UUID,
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("prompt_version", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("cost_input_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_output_tokens", sa.Integer(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("started_at", TS, nullable=True),
        sa.Column("finished_at", TS, nullable=True),
        *_ts_cols(),
    )
    op.create_index("ix_analysis_runs_tenant_id", "analysis_runs", ["tenant_id"])
    op.create_index("ix_analysis_runs_document_id", "analysis_runs", ["document_id"])

    # --- organizations (partner registry) ---
    op.create_table(
        "organizations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id",
            UUID,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("legal_name", sa.String(), nullable=False),
        sa.Column("normalized_key", sa.String(), nullable=False),
        sa.Column("pic_number", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("org_type", sa.String(), nullable=True),
        sa.Column("website", sa.String(), nullable=True),
        *_ts_cols(),
    )
    op.create_index("ix_organizations_tenant_id", "organizations", ["tenant_id"])
    op.create_index("ix_organizations_normalized_key", "organizations", ["normalized_key"])
    op.create_index("ix_organizations_pic_number", "organizations", ["pic_number"])

    # --- persons ---
    op.create_table(
        "persons",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id",
            UUID,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            UUID,
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=True),
        *_ts_cols(),
    )
    op.create_index("ix_persons_tenant_id", "persons", ["tenant_id"])

    # --- projects ---
    op.create_table(
        "projects",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id",
            UUID,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            UUID,
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "programme_id",
            UUID,
            sa.ForeignKey("programmes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "call_id",
            UUID,
            sa.ForeignKey("funding_calls.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("acronym", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("total_budget", sa.Numeric(18, 2), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("extraction_confidence", sa.Numeric(4, 3), nullable=True),
        *_ts_cols(),
    )
    op.create_index("ix_projects_tenant_id", "projects", ["tenant_id"])
    op.create_index("ix_projects_document_id", "projects", ["document_id"])
    op.create_index("ix_projects_acronym", "projects", ["acronym"])
    op.create_index("ix_projects_status", "projects", ["status"])

    # --- project_partners ---
    op.create_table(
        "project_partners",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id",
            UUID,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            UUID,
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            UUID,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("budget_share", sa.Numeric(18, 2), nullable=True),
        *_ts_cols(),
    )
    op.create_index("ix_project_partners_tenant_id", "project_partners", ["tenant_id"])
    op.create_index("ix_project_partners_project_id", "project_partners", ["project_id"])
    op.create_index(
        "ix_project_partners_organization_id", "project_partners", ["organization_id"]
    )

    # --- work_packages ---
    op.create_table(
        "work_packages",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id",
            UUID,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            UUID,
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column(
            "lead_organization_id",
            UUID,
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("budget", sa.Numeric(18, 2), nullable=True),
        *_ts_cols(),
    )
    op.create_index("ix_work_packages_tenant_id", "work_packages", ["tenant_id"])
    op.create_index("ix_work_packages_project_id", "work_packages", ["project_id"])

    # --- external_enrichment ---
    op.create_table(
        "external_enrichment",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id",
            UUID,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("owner_type", sa.String(), nullable=False),
        sa.Column("owner_id", UUID, nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        *_ts_cols(),
    )
    op.create_index("ix_external_enrichment_tenant_id", "external_enrichment", ["tenant_id"])
    op.create_index("ix_external_enrichment_owner_id", "external_enrichment", ["owner_id"])

    # --- embeddings (pgvector) ---
    op.create_table(
        "embeddings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id",
            UUID,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("owner_type", sa.String(), nullable=False),
        sa.Column("owner_id", UUID, nullable=False),
        sa.Column("chunk", sa.Text(), nullable=False),
        sa.Column("vector", Vector(1024), nullable=True),
    )
    op.create_index("ix_embeddings_tenant_id", "embeddings", ["tenant_id"])
    op.create_index("ix_embeddings_owner_id", "embeddings", ["owner_id"])

    # --- audit_log ---
    op.create_table(
        "audit_log",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id",
            UUID,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", UUID, nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("entity", sa.String(), nullable=True),
        sa.Column("entity_id", UUID, nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        *_ts_cols(),
    )
    op.create_index("ix_audit_log_tenant_id", "audit_log", ["tenant_id"])
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])

    # --- gdpr_requests ---
    op.create_table(
        "gdpr_requests",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id",
            UUID,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subject_email", sa.String(), nullable=False),
        sa.Column("request_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        *_ts_cols(),
    )
    op.create_index("ix_gdpr_requests_tenant_id", "gdpr_requests", ["tenant_id"])

    # --- api_keys ---
    op.create_table(
        "api_keys",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id",
            UUID,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("hashed_key", sa.String(), nullable=False, unique=True),
        sa.Column("scopes", sa.String(), nullable=True),
        sa.Column("last_used_at", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_ts_cols(),
    )
    op.create_index("ix_api_keys_tenant_id", "api_keys", ["tenant_id"])
    op.create_index("ix_api_keys_hashed_key", "api_keys", ["hashed_key"])


def downgrade() -> None:
    for table in [
        "api_keys",
        "gdpr_requests",
        "audit_log",
        "embeddings",
        "external_enrichment",
        "work_packages",
        "project_partners",
        "projects",
        "persons",
        "organizations",
        "analysis_runs",
        "documents",
        "user_roles",
        "users",
        "funding_calls",
        "programmes",
        "roles",
        "tenants",
    ]:
        op.drop_table(table)
