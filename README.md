# Teamora — Application Code

This `staging` branch holds **all application code** for Teamora. Project documentation
(BRD/PRD, Technical Design, SOP, QA) lives on the `main` branch, not here.

| Branch | Holds | Deploys to |
|---|---|---|
| `main` | Documentation only | — (docs site via GitHub Pages) |
| `staging` | Application code (this branch) | Staging automatically on every merge; production only from an approved release tag (`vX.Y.Z`) |

## Repository layout

```
frontend/   React + TypeScript SPA
backend/    NestJS and FastAPI services, shared libraries, DB scripts, isolation tests
.github/    CI/CD workflows (added once the pipeline runner is in place)
```

Only repo-wide files live at the root. Everything else goes inside `frontend/` or `backend/`.
The full layout rules and per-service Coolify settings are in
`Technical/Teamora_Development_Readiness_v1.0.md` §2 on `main`.

## Working on code

1. Branch from `staging`: `feature/REQ-TMR-<id>-<short-slug>` (SOP §4.1).
2. Open a pull request back into `staging`, tagged with the REQ-ID.
3. Merging into `staging` deploys to the staging server.

## Local setup

- Node.js **20.20.2** (`nvm use`, reads `.nvmrc`), Python **3.12**.
- PostgreSQL **18**, local database named `teamora`. The name is the same in every
  environment; only credentials change (Technical Stack Charter v1.1, "Database rules").
- Copy each `.env.example` to `.env` with local-only values. Never commit `.env`, and
  never put staging or production credentials on a developer machine.

Step-by-step run instructions will be added here as the first services are scaffolded.
