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

## Every service provides

| Endpoint | Meaning |
|---|---|
| `GET /health` | Liveness: 200 while the process runs. Coolify health-check path. |
| `GET /health/ready` | Readiness: 200 if the service can query its database as its own role, else 503 (no error details). |
| `/api/v1/...` | Business APIs (none yet). |

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
