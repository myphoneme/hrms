# backend/db — database bootstrap

Creates the Teamora database on a PostgreSQL 18 server: login roles, the `teamora` database,
extensions and one schema per service. **The same scripts run in every environment**; only the
credentials change (Technical Stack Charter v1.1, "Database rules").

Run it once when setting up a new server, and again whenever these scripts change. It is safe to
re-run: it only creates what's missing and re-applies grants and passwords. It never drops anything.

## What it creates

| Object | Details |
|---|---|
| Database | `teamora` (UTF-8, builtin `C.UTF-8` locale so Windows and Linux sort the same), owned by `teamora_migrator` |
| Extensions | `pgcrypto`, `citext`, `vector` in schema `extensions` (`vector` optional locally, **required** on staging/production) |
| Schemas → role | `identity` → `svc_auth`, `requisition` → `svc_requisition`, `sourcing` → `svc_publish`, `candidate` → `svc_candidate`, `dedupe` → `svc_dedupe`, `notification` → `svc_notification` |
| `teamora_migrator` | Owns every schema; the **only** role that runs migrations |
| `svc_<service>` | SELECT/INSERT/UPDATE/DELETE on its own schema only. No CREATE, no TRUNCATE, no other schemas, no `public` |

No role can bypass Row-Level Security. Migrations must `ENABLE` **and** `FORCE ROW LEVEL SECURITY`
on every multi-tenant table; with FORCE, a connection with no `app.tenant_id` set sees zero rows
(TDD §5.3).

## Required environment variables

| Variable | Purpose |
|---|---|
| `APP_ENV` | `local`, `test`, `staging` or `production` |
| `POSTGRES_MIGRATOR_PASSWORD` | Password for `teamora_migrator` |
| `POSTGRES_SVC_AUTH_PASSWORD`, `…_REQUISITION_…`, `…_PUBLISH_…`, `…_CANDIDATE_…`, `…_DEDUPE_…`, `…_NOTIFICATION_…` | One password per service role |
| `PGHOST`, `PGPORT`, `PGUSER` | Superuser connection (defaults: `localhost`, `5432`, `postgres`) |
| `PGPASSWORD` | Optional; psql prompts for the superuser password if unset |

Every password must be at least 12 characters. The bootstrap stops with a clear error if any
variable is missing or invalid, or if the server isn't PostgreSQL 18.

## Local (Windows)

```powershell
cd D:\arjun\hrms\staging\backend
Copy-Item .env.example .env      # then set your own local passwords in .env
.\db\bootstrap.ps1               # prompts for the postgres superuser password
```

## Staging / production (Coolify)

Run `backend/db/bootstrap.sh` against the Coolify-managed PostgreSQL, with the variables above set
from Coolify (never from a developer machine; SOP §8.1). How this runs as a deploy step will be
wired up with the CI/CD pipeline.

## Files

```
bootstrap.ps1                      Windows wrapper (loads backend/.env, runs psql)
bootstrap.sh                       Linux / CI wrapper
init/bootstrap.sql                 entry point: reads and validates env, then runs the steps below
init/00_database_and_roles.sql     roles + database (connected to `postgres`)
init/01_extensions.sql             extensions schema + pgcrypto, citext, vector
init/02_schemas_and_grants.sql     per-service schemas, grants, default privileges, search_path
```
