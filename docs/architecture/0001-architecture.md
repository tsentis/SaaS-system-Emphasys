# ADR 0001 — Platform Architecture

- **Status:** Accepted
- **Date:** 2026-06-30
- **Decision makers:** Emphasys Centre

## Context

Emphasys Centre needs an AI-powered platform to analyze European project proposal
PDFs (Erasmus+, Horizon Europe, CERV, Interreg, AMIF, Digital Europe), extract
structured metadata and partners, summarize them, enrich with data from official EU
sources, and store everything in a searchable database. The tool starts as an internal
product but is intended to be commercialized as a SaaS for European organizations.

## Decisions

1. **Multi-tenant from day one.** Every business table carries `tenant_id` and is
   protected by PostgreSQL Row-Level Security (RLS). A request-scoped tenant context
   sets the active tenant per connection. This avoids a costly rewrite at commercial
   launch.
2. **Backend: Python 3.12 + FastAPI.** Chosen for the strongest ecosystem around the
   highest-risk part of the system — PDF parsing, AI/LLM orchestration, and data
   extraction. FastAPI auto-generates the OpenAPI spec, giving us the public REST API
   with minimal extra work.
3. **Frontend: Next.js 15 + TypeScript** with Tailwind, shadcn/ui, and TanStack Query.
4. **AI: Anthropic Claude** — Opus 4.8 for difficult extraction, Sonnet 4.6 for
   high-volume/low-cost work — using structured tool-use so output is schema-validated.
   Every extracted field stores the producing model, a confidence score, and source
   page provenance.
5. **Auth: self-hosted JWT** (decided 2026-06-30; supersedes the earlier Clerk choice
   as the client has no Clerk account). The backend owns password hashing (bcrypt),
   JWT access/refresh tokens, and sessions. Authorization (RBAC roles/permissions) is
   owned by our database. The `users.auth_provider_id` column and a swappable
   verification layer are retained so Clerk/SSO can be added later without a rewrite.
6. **Database: PostgreSQL 16 + pgvector** — relational store and semantic search in one
   engine. SQLAlchemy 2.0 + Alembic for models and migrations.
7. **Async processing: Celery + Redis.** PDF analysis is slow and must run off the
   request path as a worker pipeline.
8. **Object storage: S3-compatible** (MinIO in dev, S3 in prod). PDFs are stored in
   object storage, not the database.
9. **GDPR-ready by design** even though no hard constraint exists yet: audit log,
   right-to-erasure support, and zero-retention Anthropic API terms. Cheap to keep now,
   expensive to retrofit.

## Extraction pipeline

```
upload → text extraction (pdfplumber/pypdf) → OCR fallback (Tesseract) →
chunk → LLM structured extraction (tool-use schema) → Pydantic validation →
partner entity resolution → persist (confidence + page provenance) →
vector embeddings (pgvector)
```

Runs as a Celery job; never inline with the HTTP request.

## Data model (core)

`tenants`, `users`, `roles`, `user_roles`, `documents`, `analysis_runs`, `programmes`,
`funding_calls`, `projects`, `organizations` (partner registry, deduped via
`normalized_key`/PIC), `project_partners`, `persons`, `work_packages`,
`external_enrichment`, `embeddings`, `audit_log`, `gdpr_requests`, `api_keys`.

See `backend/alembic/versions/` for the authoritative schema.

## Milestones

0. Scaffolding (this milestone) — infra, app shells, base schema.
1. Auth + tenancy + users/RBAC
2. Document upload & management
3. AI extraction pipeline (single proposal) — first end-to-end vertical slice
4. Partner/organization registry + entity resolution
5. Search & filtering
6. Dashboards & analytics
7. Exports (Excel / CSV / PDF / Word)
8. External enrichment (CORDIS, Funding & Tenders Portal)
9. Public REST API + API keys
10. GDPR hardening + SaaS billing

## Open (non-blocking) questions

- EC data source access: do we have API keys for the Funding & Tenders Portal, or build
  defensively on public endpoints (CORDIS first)?
- Proposal languages: assumed multilingual (Claude handles natively).
- Year-one scale: assumed low hundreds of PDFs/month, < 50 users.

## Consequences

- One codebase serves all tenants; tenant isolation is enforced in the database, not
  only in application code.
- Reliance on two external providers (Anthropic, Clerk) — acceptable; both have
  migration paths if needed.
