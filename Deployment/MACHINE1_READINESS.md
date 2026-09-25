# Teamora Machine1 / Machine A Readiness

> **Historical snapshot (2026-09-21, old VM).** Superseded: development moved to a local Windows 11 machine on 2026-09-25, and the backend is Python/FastAPI only (`Technical/Teamora_Technical_Stack_Charter_v1.2.md`). Current setup and run instructions: `backend/README.md` on the `staging` branch and the `phoneme-dev-machine-setup` Skill.

## Scope

This workstation is the developer environment defined by `Phoneme_SDLC_SOP_v1.2` Section 8.1. QA Machine B remains an independent environment and must test the deployed staging build, not this workstation.

## Repository baseline reviewed

- `Requirement/Teamora_BRD_PRD_v2.4.docx`: Release 1 is Module 1 (JD Intake & Freezing) and Module 2 (Candidate Sourcing & Resume Aggregation); both are Draft pending Reviewed/Approved sign-off.
- `Technical/Teamora_TechDesign_M1M2_v4.2.docx`: React/TypeScript SPA, NestJS services, FastAPI services, PostgreSQL, Redis, Kafka, OpenSearch, MinIO, Vault, and REST APIs behind a tenant-aware gateway.
- `Technical/Teamora_Technical_Stack_Charter_v1.0.md`: Node.js 20.x + npm; Python 3.12 + pip; GitHub Actions and Coolify interim deployment topology.
- `UI-UX/teamora_hr_suite.html` and `UI-UX/Teamora_UI_UX_Mockups.pdf`: Teamora brand/UI reference; product name `Teamora`, tagline `People. Potential. Progress.`.
- `Quality Assurance/Phoneme_HR_Suite_Test_Cases_v1.0.xlsx`: 67 test cases across Modules 1–2 and platform/NFR coverage.
- `Deployment/Phoneme_SDLC_SOP_v1.2.docx`: Machine A checklist, branch/REQ-ID discipline, staging flow, and independent QA gate.

## Completed on this workstation

- Git is installed and the repository remote is `git@github.com:myphoneme/hrms.git`.
- Git identity is configured as `arjun kushwaha <arjun.kushwah@myphoneme.com>`.
- Python 3.12.10 and pip are installed.
- Node.js 20.20.2 LTS is downloaded, SHA-256 verified, and available in the ignored local `.tools/` cache.
- Runtime pins are recorded in `.nvmrc` and `.node-version`.

## Not yet available / blocked

- Docker/Compose, PostgreSQL client, Redis CLI, GitHub CLI, and WSL are not installed or available.
- No application source tree, `package.json`, lockfile, Python requirements file, `.env.example`, pre-commit configuration, or test/build scripts exist yet.
- Therefore the SOP's clean baseline build/test cannot be executed until the initial service scaffold and lockfiles are committed.
- GitHub SSH key registration, repository branch creation, Coolify applications/secrets, and Jira/Zephyr access require account/owner actions and are not performed automatically here.

## Next development gate

1. Confirm the initial monorepo layout and first service ownership against the pending BRD/PRD/TDD approval.
2. Scaffold the React frontend, NestJS services, and FastAPI services with committed manifests and lockfiles.
3. Add dev-safe `.env.example`, lint/format/pre-commit hooks, health endpoints, and local service orchestration.
4. Run the clean baseline build/unit suite on Machine1.
5. Create `staging` and begin work on a branch named `feature/REQ-TMR-<id>-<short-slug>` only after selecting the first BRD REQ-ID.
