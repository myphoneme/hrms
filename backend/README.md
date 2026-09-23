# backend

Teamora backend services and shared code. Each service in `services/` deploys as its **own**
Coolify application with Base Directory `/backend`, so its image can include the shared code below.

Planned layout:

```
services/
  auth-service/              NestJS    [platform]
  requisition-service/       NestJS    [M1]
  notification-service/      NestJS    [platform]
  jd-generation-service/     FastAPI   [M1]
  publish-service/           NestJS    [M2]
  candidate-service/         NestJS    [M2]
  resume-parsing-service/    FastAPI   [M2]
  dedupe-service/            FastAPI   [M2]
packages/                    shared TypeScript: contracts (OpenAPI + events), tenancy, auth-guards, config
python-libs/teamora_common/  shared Python: tenancy, auth, health, logging
db/init/                     database / schema / role bootstrap SQL (same scripts in every environment)
tests/isolation/             cross-tenant / cross-client isolation suite
docker-compose.dev.yml       local Redis and other supporting services
package.json                 npm workspaces for services/* (NestJS) and packages/*
.env.example
```

Services are added only when a REQ-ID needs them. The first milestone is
`auth-service` + `requisition-service` with health endpoints.
