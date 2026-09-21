# Teamora — Technical Stack Charter v1.0

Companion reference for `phoneme-technical-stack`. Extracted and formalized from
`Teamora_TechDesign_M1M2_v4.2.docx` Sections 17–19 (the stack decisions already
existed there but were never filed as a standalone charter) plus the SOP v1.1 /
`Deployment/ci-cd/` deployment topology decision made 2026-09-18.

| Field | Decision |
|---|---|
| **1. Product type** | Multi-tenant SaaS web app (HR suite: recruitment/JD/resume modules M1–M2, more to follow) |
| **2. Frontend** | React + TypeScript SPA, Tailwind CSS. Served as static assets. |
| **3. Backend** | Polyglot microservices per Tech Design §17.2: **NestJS (TypeScript)** — Auth/AAA, Notification (+BullMQ), Requisition (M1), Scoring Matrix (M1). **Python/FastAPI** — JD Generation (M1, + third-party LLM API), Resume Parsing (M2, + pdfplumber/textract), Dedupe (M2, + pgvector). REST APIs behind a shared tenant-aware API gateway. |
| **4. Data** | PostgreSQL (primary datastore, Patroni-managed HA + read replicas, pgvector extension), Redis (sessions, cache, queues), Kafka (async parse jobs), OpenSearch (candidate/resume search index), MinIO (object storage — resumes, offer docs), HashiCorp Vault (native KMS, HSM-backed via PKCS#11 — Tech Design §4.0). |
| **5. AI/ML components** | JD Generation Service calls a third-party LLM API (Release 1 default per Tech Design §16); human-in-the-loop review/edit required before a generated JD is published (per BRD/PRD). No fine-tuned/self-hosted model for Release 1. |
| **6. Hosting & infra** | **On Phoneme's own infrastructure.** ⚠️ See "Known divergence" below — Tech Design §18 specifies on-prem Kubernetes; the currently-adopted deployment path (2026-09-18 decision) is **Coolify** on one or more Phoneme-owned VMs, one Coolify application per service per environment (`staging`, `production`). Domain pattern: `<service>.staging.teamora.<domain>` / `<service>.teamora.<domain>` — TBD, confirm with Release Owner. |
| **7. Third-party integrations** | Job boards (Naukri RMS — contract pending), LLM API provider (TBD which vendor), email/SMS/WhatsApp notification providers (TBD which vendor), SSO providers (per Tech Design auth section). |
| **8. DevOps & CI/CD** | GitHub (repo hosting). Branches: feature → `staging` → `main`. Pipeline: GitHub Actions build+test → Coolify webhook redeploy for staging (auto); GitHub Actions full regression → `production` Environment approval (Release Owner) → Coolify webhook redeploy + smoke test + auto-rollback for production. See `Deployment/ci-cd/`. |
| **9. Security & compliance baseline** | DPDP Act 2023 (Indian personal data). Argon2id password hashing, TOTP MFA. Tenant isolation via PostgreSQL Row-Level Security + mandatory query-builder middleware (Tech Design §5.3). Column-level encryption with per-tenant DEK; Vault-issued keys, HSM-backed root key, annual rotation default. |
| **10. Coding conventions** | TBD — not yet written. Recommend: one repo folder per service (`services/<service-name>/`) if monorepo, or confirm polyrepo instead; per-language lint/format (ESLint+Prettier for NestJS/React, ruff/black for FastAPI) before first commit lands. |

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
