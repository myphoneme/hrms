# backend

Teamora backend: Python **FastAPI** services and their shared library. Each service in `services/`
deploys as its **own** Coolify application with Base Directory `/backend`, so its image can include the
shared code below. (Decision 2026-09-25: one backend language, FastAPI everywhere; replaces the earlier
NestJS + FastAPI split.)

## Layout

```
services/
  auth-service/              [platform]  port 3001   role svc_auth          schema identity      ✅ skeleton
  requisition-service/       [M1]        port 3002   role svc_requisition   schema requisition   ✅ FR-007, FR-004, FR-006, FR-005
  notification-service/      [platform]  (planned)
  jd-generation-service/     [M1]        (planned)
  publish-service/           [M2]        (planned)
  candidate-service/         [M2]        (planned)
  resume-parsing-service/    [M2]        (planned)
  dedupe-service/            [M2]        (planned)
python-libs/teamora_common/  shared: config checks, DB pool, with_tenant, access tokens, error format,
                             migrations runner, health endpoints, app factory
db/                          database bootstrap (roles, database, schemas) — see db/README.md
dev/                         local manual-testing kit — see dev/README.md
constraints.txt              exact versions of every Python dependency (local, CI and Docker)
requirements-dev.txt         editable installs of all packages + pytest / ruff
pyproject.toml               pytest and ruff settings for the whole backend
.env.example                 variable names shared by every environment
```

Each service is a small Python package, `services/<service>/src/<package>/`:

```
__init__.py        SERVICE (name, port, DB role) and build_app()
__main__.py        python -m <package>            -> runs the service
migrate.py         python -m <package>.migrate    -> applies its schema migrations
migrations/        NNNN_description.sql (plain SQL, shipped inside the image)
<feature>.py       one module per feature: request models, router and SQL together
tests/             pytest; files named test_db_*.py need a real database
```

Services are added only when a REQ-ID needs them.

## Run locally (Windows)

Prerequisites: Python **3.12** (3.11 also works locally), PostgreSQL 18 with the database bootstrapped
(`db/README.md`), and `backend/.env` created from `.env.example`.

```powershell
cd D:\arjun\hrms\staging\backend
python -m venv .venv
.venv\Scripts\python -m pip install -c constraints.txt -r requirements-dev.txt
.venv\Scripts\Activate.ps1

python -m auth_service.migrate --env-file .env            # identity first...
python -m requisition_service.migrate --env-file .env     # ...then the schemas that reference it
python -m requisition_service --env-file .env             # http://localhost:3002/health
python -m auth_service --env-file .env                    # http://localhost:3001/health (second terminal)
```

Every service reads the same `backend/.env`. Don't set `PORT` there; each service uses its own default port.

**Manual checks in a browser:** see [`dev/README.md`](dev/README.md): demo data (`python dev/seed.py`), a
token (`python dev/make_token.py`) and the interactive API page at http://localhost:3002/api/docs
(local/test only).

## Tests and lint

```powershell
ruff check .; ruff format --check .      # lint + formatting
pytest                                   # unit / API tests (no database)
pytest -m db                             # database tests (see below)
```

`pytest -m db` runs the tenant-isolation and business-rule tests against a real, bootstrapped and migrated
database, logged in as each service's own role. Use a separate test database, never your dev data
(Charter, Database rules): for example a throwaway server on another port, with `APP_ENV=test`,
`POSTGRES_PORT`/`PGPORT` pointing at it and test-only passwords set in the shell; then
`sh db/bootstrap.sh`, run both migrations, and `pytest -m db`.

CI runs all of this on every PR (`.github/workflows/backend-ci.yml`): lint + tests, database tests on
PostgreSQL 18 + pgvector, and per service a Docker build, migrations from the image and a health check.

## Database migrations

Each service owns the migrations for its own schema, as plain SQL in `src/<package>/migrations/`
(`NNNN_description.sql`, applied in order, each in its own transaction, recorded in
`<schema>.schema_migrations`). They run as `teamora_migrator`, never as the service role, so service roles
never own a table and cannot bypass Row-Level Security.

Rules for every migration that creates a multi-tenant table: `ENABLE` **and** `FORCE ROW LEVEL SECURITY`,
and a policy on `current_setting('app.tenant_id', true)`. Service code queries those tables only inside
`with with_tenant(pool, TenantScope(tenant_id)) as db:` from `teamora_common`.

## Every service provides

| Endpoint | Meaning |
|---|---|
| `GET /health` | Liveness: 200 while the process runs. Coolify health-check path. |
| `GET /health/ready` | Readiness: 200 if the service can query its database as its own role, else 503 (no error details). |
| `/api/v1/...` | Business APIs. Require `Authorization: Bearer <access token>` (`auth: Auth` parameter). |
| `GET /api/docs` | Interactive API page (Swagger UI) — only when `APP_ENV` is `local` or `test`. |

Errors always come back as `{ "reason", "message", "details"? }`; invalid request bodies as
`422 validation_failed` with `details: [{ field, problem }]` listing every problem at once.

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
| requisition-service | `GET` / `PUT /api/v1/sla-policy` | HR-M1-FR-005 (TDD §16.5) | The tenant's approval SLA: `{ reminder_after_business_days, escalate_after_business_days, timezone }` (defaults 3 / 5 / Asia/Kolkata; reminder 1–20, escalation 2–30 and later than the reminder). `PUT` is `tenant_admin` only (`403 role_not_allowed`). Business days are Mon–Fri in that time zone; public holidays aren't counted in Release 1. |
| requisition-service | `GET /api/v1/requisitions/{id}/sla` | HR-M1-FR-005 | The requisition's SLA clock (`pending_since`, `reminder_due_at`, `escalation_due_at`, open/resolved and why) and its reminders/escalations. |
| requisition-service | `GET /api/v1/sla-events?kind=&delivery_status=` | HR-M1-FR-005 | Reminders and escalations: `recruiter_hr` / `tenant_admin` see the whole tenant, a manager only their own reminders. Events wait with `delivery_status: pending` for the Notification Service. |

At startup each service logs its `APP_ENV` and database target, e.g.
`requisition-service listening on :3002 | APP_ENV=local | DB=svc_requisition@localhost:5432/teamora`, and
refuses to start, listing every problem, if `APP_ENV`, `POSTGRES_HOST`, `AUTH_JWT_SECRET` or its role
password is missing, or if `POSTGRES_DB` isn't `teamora`.

## Approval SLA check (HR-M1-FR-005)

Sending a JD version for approval starts an SLA clock (database trigger). A scheduled check records a
**reminder** for the manager once the tenant's reminder threshold has passed, then an **escalation** for HR
once the escalation threshold has passed — unless the manager has responded (freeze, a new version, rejection)
or the requisition is OnHold/Closed, which stops the clock. The check runs inside requisition-service every
`SLA_CHECK_INTERVAL_SECONDS` (default 300; `0` turns it off), and can be run once by hand or from a scheduled
task: `python -m requisition_service.sla --env-file .env`. Running it twice at once is safe (each reminder and
escalation is recorded at most once). Delivery by email/portal comes with the Notification Service.

## Adding a new service

1. Copy `services/auth-service/` to `services/<name>/` and rename the package folder to `<name_with_underscores>`.
2. In `pyproject.toml`, `__init__.py` (`SERVICE`), `migrate.py` and the `Dockerfile`, replace the service
   name, port, DB role (`svc_<name>`), password variable (`POSTGRES_SVC_<NAME>_PASSWORD`) and schema.
3. Add it to `requirements-dev.txt`, the `known-first-party` list in `pyproject.toml`, and the CI matrix.
4. If the service owns a schema, add its role and schema to `db/init/` first.

## Docker

Build context is `backend/`:

```
docker build -f services/requisition-service/Dockerfile -t teamora-requisition-service .
```

The image runs as a non-root user (`app`) and contains the service's migrations: run
`python -m <package>.migrate` from the same image as a deploy step before starting the new version.
