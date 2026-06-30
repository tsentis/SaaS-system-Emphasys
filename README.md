# Emphasys European Project Intelligence Platform

AI-powered platform that analyzes European project proposal PDFs (Erasmus+, Horizon
Europe, CERV, Interreg, AMIF, Digital Europe, …), extracts structured information,
recognizes partner organizations, summarizes proposals, enriches data from official
EU sources, and stores everything in a normalized, multi-tenant PostgreSQL database.

Built internal-first, designed from day one to be commercialized as a SaaS platform
for European organizations.

## Status

🚧 **Milestone 1 — Auth, tenancy & RBAC.** Self-hosted JWT auth, multi-tenant
registration/login, role-based access control, and two-layer tenant isolation on top
of the Milestone 0 skeleton.

See [docs/architecture/0001-architecture.md](docs/architecture/0001-architecture.md)
for the full architecture and roadmap.

## Tech stack

| Layer       | Technology |
|-------------|------------|
| Backend     | Python 3.12 · FastAPI · SQLAlchemy 2.0 · Alembic · Pydantic |
| AI          | Anthropic Claude (Opus 4.8 / Sonnet 4.6) via structured tool-use |
| Database    | PostgreSQL 16 + pgvector (multi-tenant, row-level security) |
| Async jobs  | Celery + Redis |
| Storage     | S3-compatible (MinIO in dev) |
| Frontend    | Next.js 15 · TypeScript · Tailwind · shadcn/ui · TanStack Query |
| Auth        | Clerk (managed) — JWT verified by the backend |
| Exports     | openpyxl · python-docx · WeasyPrint · csv |

## Quick start (development)

Prerequisites: Docker Desktop.

```bash
cp .env.example .env          # fill in secrets (Anthropic key, Clerk keys, …)
docker compose up --build     # starts db, redis, minio, backend, frontend
```

- Backend API + docs: http://localhost:8000/docs
- Health check:        http://localhost:8000/api/v1/health
- Frontend:            http://localhost:3000
- MinIO console:       http://localhost:9001

### Database migrations

```bash
docker compose exec backend alembic upgrade head      # apply migrations
docker compose exec backend alembic revision -m "msg" # create a new one
```

Run `alembic upgrade head` before first use — it creates the schema, seeds the RBAC
roles (`admin`, `analyst`, `viewer`), and installs the Row-Level Security policies.

### Authentication (self-hosted JWT)

- `POST /api/v1/auth/register` — creates a new tenant + its first **admin** user, returns tokens.
- `POST /api/v1/auth/login` — `{tenant_slug, email, password}` → access + refresh tokens.
- `POST /api/v1/auth/refresh` — exchange a refresh token for fresh tokens.
- `GET  /api/v1/auth/me` — current user profile (send `Authorization: Bearer <access>`).
- `GET/POST /api/v1/users …` — tenant user management (admin only).

### Tenant isolation

Two layers: (1) an **application-layer guard** auto-filters every query on a
tenant-scoped model by the request's tenant; (2) **PostgreSQL Row-Level Security**
policies as defense in depth. RLS is only enforced when the app connects as a
*non-superuser* role — for production, create a dedicated login role and point the
backend's `DATABASE_URL` at it. In development (superuser connection) the
application-layer guard is the active enforcement.

### Testing

```bash
cd backend
pip install -r requirements.txt
pytest                                   # unit tests (no DB) always run
TEST_DATABASE_URL=postgresql+psycopg://emphasys:change-me-in-prod@localhost:5432/emphasys_test \
  pytest                                 # also runs DB-backed integration tests
```

Integration tests (auth flow, RBAC, cross-tenant isolation) skip automatically when
`TEST_DATABASE_URL` is unset or unreachable.

## Repository layout

```
backend/    FastAPI service, models, services, AI pipeline, migrations
frontend/   Next.js app
docs/       Architecture decision records & API docs
infra/      Deployment / IaC (added in a later milestone)
```

## Roadmap (milestones)

0. **Scaffolding** ✅
1. Auth + tenancy + users/RBAC ← current
2. Document upload & management
3. AI extraction pipeline (single proposal)
4. Partner/organization registry + entity resolution
5. Search & filtering
6. Dashboards & analytics
7. Exports (Excel / CSV / PDF / Word)
8. External enrichment (CORDIS, Funding & Tenders Portal)
9. Public REST API + API keys
10. GDPR hardening + SaaS billing

## License

Proprietary — © Emphasys Centre. All rights reserved.
