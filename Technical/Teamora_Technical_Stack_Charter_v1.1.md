# Teamora — Technical Stack Charter v1.1

Companion reference for `phoneme-technical-stack`. Extracted and formalized from
`Teamora_TechDesign_M1M2_v4.2.docx` Sections 17–19 (the stack decisions already
existed there but were never filed as a standalone charter) plus the SOP v1.1 /
`Deployment/ci-cd/` deployment topology decision made 2026-09-18.
v1.1 adds the database rules and the documentation/code branch split decided 2026-09-23
(see `Technical/Teamora_Development_Readiness_v1.0.md` for the full reasoning).

| Field | Decision |
|---|---|
| **1. Product type** | Multi-tenant SaaS web app (HR suite: recruitment/JD/resume modules M1–M2, more to follow) |
| **2. Frontend** | React + TypeScript SPA, Tailwind CSS. Served as static assets. |
| **3. Backend** | Polyglot microservices per Tech Design §17.2: **NestJS (TypeScript)** — Auth/AAA, Notification (+BullMQ), Requisition (M1), Scoring Matrix (M1). **Python/FastAPI** — JD Generation (M1, + third-party LLM API), Resume Parsing (M2, + pdfplumber/textract), Dedupe (M2, + pgvector). REST APIs behind a shared tenant-aware API gateway. ⚠️ Tech Design §17.2 also names Kong (gateway) and Go (Audit, channel adapters); Release 1 position pending — Readiness doc Blocker B5. |
| **4. Data** | **PostgreSQL 18** (primary datastore; pgvector extension; Row-Level Security; Patroni-managed HA + read replicas as the production target state), Redis (sessions, cache, queues), Kafka (async parse jobs), OpenSearch (candidate/resume search index), MinIO (object storage — resumes, offer docs), HashiCorp Vault (native KMS, HSM-backed via PKCS#11 — Tech Design §4.0). **Database rules: see the section below.** |
| **5. AI/ML components** | JD Generation Service calls a third-party LLM API (Release 1 default per Tech Design §16); human-in-the-loop review/edit required before a generated JD is published (per BRD/PRD). No fine-tuned/self-hosted model for Release 1. |
| **6. Hosting & infra** | **On Phoneme's own infrastructure.** ⚠️ See "Known divergence" below — Tech Design §18 specifies on-prem Kubernetes; the currently-adopted deployment path (2026-09-18 decision) is **Coolify** on one or more Phoneme-owned VMs (staging: `10.100.60.119`), one Coolify application per service per environment (`staging`, `production`). Domain pattern: `<service>.staging.teamora.<domain>` / `<service>.teamora.<domain>` — TBD, confirm with Release Owner. |
| **7. Third-party integrations** | Job boards (Naukri RMS — contract pending), LLM API provider (TBD which vendor), email/SMS/WhatsApp notification providers (TBD which vendor), SSO providers (per Tech Design auth section). |
| **8. DevOps & CI/CD** | GitHub (repo hosting, `myphoneme/hrms`). **Branches (decided 2026-09-23): `main` = project documentation only; `staging` = all application code.** Feature branches `feature/REQ-TMR-<id>-<slug>` are cut from and merged back into `staging`. Pipeline: GitHub Actions build+test → Coolify redeploy for staging (auto). **Staging and production both deploy from the `staging` branch** (decided 2026-09-23). Production deploys only an approved release, a tagged commit on `staging` (`vX.Y.Z`): GitHub Actions full regression → `production` Environment approval (Release Owner) → Coolify redeploy + smoke test + rollback. SOP v1.9 update pending. See `Deployment/ci-cd/`. |
| **9. Security & compliance baseline** | DPDP Act 2023 (Indian personal data). Argon2id password hashing, TOTP MFA. Tenant isolation via PostgreSQL Row-Level Security + mandatory query-builder middleware (Tech Design §5.3). Column-level encryption with per-tenant DEK; Vault-issued keys, HSM-backed root key, annual rotation default. |
| **10. Coding conventions** | **Repo layout decided 2026-09-23:** code on `staging` is split into two top-level folders, `frontend/` (React SPA) and `backend/` (`services/<service-name>/`, `packages/`, `python-libs/`, `db/init/`, `tests/isolation/`); only `.github/`, `README.md` and repo config stay at the root. Each backend service is its own Coolify application (Base Directory `/backend`, per-service Dockerfile and watch paths). Remaining conventions proposed in `Teamora_Development_Readiness_v1.0.md` §2 (Drizzle ORM for NestJS, SQLAlchemy 2 + Alembic for FastAPI; ESLint+Prettier / ruff+black) — confirm before first commit. |

## Database rules (decided 2026-09-23)

1. **Local development uses a local database.** It runs on the developer's own machine (Machine A: native PostgreSQL 18).
2. **Staging uses the real remote database.** It's the Coolify-managed PostgreSQL on the staging server, reachable only from the staging application on Coolify's internal network. Production uses its own separate remote instance.
3. **The database name is `teamora` in every environment:** local, CI, staging and production. Schema names (`identity`, `requisition`, `sourcing`, `candidate`, `dedupe`, `notification`) and role names (`teamora_migrator`, `svc_<service>`) are also identical everywhere.
4. **Only the credentials change between environments:** host, port, passwords and the connection string. They're supplied through the same environment variable names (`APP_ENV`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_*_USER`, `POSTGRES_*_PASSWORD`): a local `.env` on developer machines, Coolify environment variables on staging and production. Never committed to Git.
5. Developer machines never hold staging or production credentials (SOP §8.1). Changes reach staging only through the pipeline.
6. The same bootstrap SQL (`backend/db/init/`) and the same migrations run in every environment. Staging and production migrations run as a deploy step, never by hand from a developer machine.
7. Safeguards, because the names are identical: services log `APP_ENV` and the DB host at startup; destructive scripts (reset/seed/drop) run only when `APP_ENV` is `local` or `test`; staging and production Postgres ports aren't published outside the Coolify server.
8. PostgreSQL major version **18** in every environment. Containers use `pgvector/pgvector:pg18`.

## Known divergence — flagged, not silently resolved

Tech Design v4.2 §18–19 designs a **target-state** deployment architecture: self-managed
Kubernetes (two node pools), GitOps via ArgoCD, per-service signed container images in an
immutable registry, SCA/container vulnerability scanning, and canary rollout (5% traffic)
with automated SLO-triggered rollback.

On 2026-09-18, the team chose to build and onboard against the **simpler Coolify + GitHub
Actions pipeline** already scaffolded in `Deployment/ci-cd/` instead, for faster initial
setup. This is a deliberate interim decision, not a silent substitution:

- No GitOps, no canary, no automated container vulnerability scanning, no signed images
  in this interim pipeline. Rollback is Coolify's redeploy-previous-build webhook, not a
  GitOps revert.
- Each of the microservices in §17.2 gets its own Coolify application (staging + production)
  rather than a shared Kubernetes manifest set.
- **Revisit before this scales past early Release 1 traffic**, and definitely before the
  compliance/security posture implied by Tech Design §18–19 (SAST/SCA gates, signed images)
  is actually required — Tech Design should either be updated to reflect Coolify as the
  accepted Release 1 topology, or the pipeline should be migrated to match Tech Design
  before general availability. Whoever owns that call should add a changelog line here
  when it happens.

## Changelog

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0 | 2026-09-18 | Claude (session with arjun kushwaha) | Initial charter, formalizing decisions already implicit in Tech Design v4.2 §17 and the SOP v1.1 Coolify pipeline; flagged the K8s/GitOps vs. Coolify divergence per user decision. |
| 1.1 | 2026-09-23 | Claude (session with arjun kushwaha) | Added "Database rules" section (local DB for development, real remote DB for staging, database name `teamora` identical in every environment with only credentials changing, PostgreSQL 18 everywhere) per arjun kushwaha's decision. Row 8 updated for the `main` = docs / `staging` = code branch split, with production source flagged as pending (Readiness B2). Row 3 flags the Kong/Go gap (Readiness B5). Row 10 records the `frontend/` + `backend/` repo layout. Row 8 records that staging and production both deploy from `staging` (production via approved release tags). |
