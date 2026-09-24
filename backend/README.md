# backend

Teamora backend services and shared code. Each service in `services/` deploys as its **own**
Coolify application with Base Directory `/backend`, so its image can include the shared code below.

## Layout

```
services/
  auth-service/              NestJS    [platform]  port 3001   role svc_auth          ✅ skeleton
  requisition-service/       NestJS    [M1]        port 3002   role svc_requisition   ✅ skeleton
  notification-service/      NestJS    [platform]  (planned)
  jd-generation-service/     FastAPI   [M1]        (planned)
  publish-service/           NestJS    [M2]        (planned)
  candidate-service/         NestJS    [M2]        (planned)
  resume-parsing-service/    FastAPI   [M2]        (planned)
  dedupe-service/            FastAPI   [M2]        (planned)
packages/
  platform/                  @teamora/platform: config validation, DB pool, /health endpoints, startup
  (planned) contracts/, tenancy/, auth-guards/
python-libs/teamora_common/  (planned) shared Python: tenancy, auth, health, logging
db/                          database bootstrap — see db/README.md
tests/isolation/             (planned) cross-tenant / cross-client isolation suite
package.json                 npm workspaces: packages/* then services/*
tsconfig.base.json           shared TypeScript settings
.env.example                 variable names shared by every environment
```

Services are added only when a REQ-ID needs them.

## Run locally (Windows, Machine A)

Prerequisites: Node **24 LTS** (`.nvmrc` pins 24.21.0; `nvm install 24.21.0` then `nvm use 24.21.0`), PostgreSQL 18 with the database bootstrapped
(`db/README.md`), and `backend/.env` created from `.env.example`.

```powershell
cd E:\Arjun-kushwaha\projects\hrms\staging\backend
npm install
npm run build
npm test
npm run start:auth           # http://localhost:3001/health
npm run start:requisition    # http://localhost:3002/health  (second terminal)
```

Both services read `backend/.env`. Don't set `PORT` there; each service uses its own default port.

## Database migrations

Each service owns the migrations for its own schema, as plain SQL in `services/<service>/db/migrations/`
(`NNNN_description.sql`, applied in order, each in its own transaction). They run as `teamora_migrator`,
never as the service role, so service roles never own a table and cannot bypass Row-Level Security.

```powershell
npm run migrate:local        # applies pending migrations to the database in backend/.env
```

Rules for every migration that creates a multi-tenant table: `ENABLE` **and** `FORCE ROW LEVEL SECURITY`,
and a policy on `current_setting('app.tenant_id', true)`. Service code queries those tables only through
`withTenant(pool, { tenantId, clientId }, fn)` from `@teamora/platform`.

## Database tests

`npm run test:db` runs the tenant-isolation tests against a real, bootstrapped and migrated database, logged
in as each service's own role. Use a separate test instance, never your dev data (Charter v1.1, Database
rules): for example a throwaway container on port 5433.

```powershell
docker run -d --name teamora-test-db -e POSTGRES_PASSWORD=<test-only> -p 5433:5432 pgvector/pgvector:pg18
# then, with PGPORT/POSTGRES_PORT=5433, APP_ENV=test and test-only passwords set in the shell:
sh db/bootstrap.sh
npm run migrate
npm run test:db
```

CI runs the same steps on every PR (`.github/workflows/backend-ci.yml`, job "Database tests").

## Every service provides

| Endpoint | Meaning |
|---|---|
| `GET /health` | Liveness: 200 while the process runs. Coolify health-check path. |
| `GET /health/ready` | Readiness: 200 if the service can query its database as its own role, else 503 (no error details). |
| `/api/v1/...` | Business APIs. Require `Authorization: Bearer <access token>` (`AuthGuard`). |

Errors always come back as `{ "reason", "message", "details"? }`.

## APIs

| Service | Endpoint | Requirement | Notes |
|---|---|---|---|
| requisition-service | `POST /api/v1/requisitions/intake` | HR-M1-FR-007 (TDD §8) | Body `{ tenant_id, client_id, department_id?, raw_brief_text, source: "email" \| "portal" }` → `201 { requisition_id, status: "Draft" }`. `client_id` must always be present: a staffing-agency tenant must name one of its own clients (`422 client_required` / `unknown_client`), a direct employer must send `null` (`422 client_not_allowed`). `tenant_id` must match the token (`403 tenant_mismatch`). |
| requisition-service | `GET /api/v1/requisitions/{id}/jd-versions` | HR-M1-FR-004 (TDD §8) | Full version history in version order, including Approved / Superseded / Rejected. |
| requisition-service | `POST /api/v1/requisitions/{id}/jd-versions` | HR-M1-FR-004 | Every edit is a new version: `{ content, variant_type?, based_on_version_id? }` → `201`. First draft = `Draft`; a revision of an existing version = `Revising`. `409 requisition_not_editable` when OnHold/Closed. |
| requisition-service | `POST /api/v1/requisitions/{id}/jd-versions/{versionId}/submit` | HR-M1-FR-004 | Draft/Revising → `PendingApproval`; anything else `409 version_not_submittable`. |
| requisition-service | `PATCH /api/v1/requisitions/{id}/jd-versions/{versionId}` | HR-M1-FR-004 (TDD §15) | Always `409 version_immutable`: versions are never edited in place; create a new version based on it. The database enforces this too (content immutable, allowed status transitions only, no deletes). |
| requisition-service | `GET /api/v1/requisitions/{id}/jd-versions/{versionId}/scoring-matrix/draft` | HR-M1-FR-006 (TDD §8) | The version's draft matrix (created empty on first read): `{ matrix_id, status, matrix_revision, criteria[], current_total_percent }`. |
| requisition-service | `POST .../scoring-matrix/draft/criteria` · `DELETE .../criteria/{criterionId}?matrix_revision=N` | HR-M1-FR-006 | Add / remove a criterion (manual stand-in until generation, HR-M1-FR-001). Categories: `core_skills`, `experience_seniority`, `domain_competency`, `education_fit` — no soft skills. |
| requisition-service | `PATCH .../scoring-matrix/draft` | HR-M1-FR-006 (TDD §8) | `{ matrix_revision, criteria: [{ criterion_id, weight_percent }] }`; weights 0–100; the total is checked only at freeze. Stale `matrix_revision` → `409 revision_mismatch` with the current state. |
| requisition-service | `POST /api/v1/requisitions/{id}/freeze` | HR-M1-FR-006 (TDD §8) | `{ approved_version_id, expected_active_version_id }` → approves the PendingApproval version **and** its matrix in one transaction, supersedes the previous one → `Frozen_Open`. Exact repeat → 200 no-op; `409 stale_expected_version` / `version_not_approvable` / `matrix_total_invalid` (with the total). |
| requisition-service | `GET /api/v1/requisitions/{id}/scoring-matrix` | HR-M1-FR-006 (TDD §8) | The Approved matrix of the active version. |

At startup each service logs its `APP_ENV` and database target, e.g.
`listening on :3001 | APP_ENV=local | DB=svc_auth@localhost:5432/teamora`, and refuses to start,
listing every problem, if `APP_ENV`, `POSTGRES_HOST` or its role password is missing, or if
`POSTGRES_DB` isn't `teamora`.

## Adding a new NestJS service

1. Copy `services/auth-service/` to `services/<name>/`.
2. In `package.json`, `src/service.ts`, `Dockerfile` and `test/`, replace the service name, port, DB role
   (`svc_<name>`) and password variable (`POSTGRES_SVC_<NAME>_PASSWORD`).
3. If the service owns a schema, add its role and schema to `db/init/` first.

## Docker

Build context is `backend/`:

```
docker build -f services/auth-service/Dockerfile -t teamora-auth-service .
```
