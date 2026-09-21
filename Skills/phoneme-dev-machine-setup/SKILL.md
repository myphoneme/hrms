---
name: phoneme-dev-machine-setup
description: Walk a developer through setting up Machine A (their local development environment) for a Phoneme product, per SOP Section 8.1 — so onboarding a new developer follows the same checklist every time instead of drifting per person.
---

# Phoneme Machine A — Developer Environment Setup

Onboarding companion to `Phoneme_SDLC_SOP_v1.1.docx` Section 8.1. "Machine A" is
SOP terminology for a developer's own laptop/workstation — kept deliberately
separate from Machine B (QA, see `phoneme-qa-machine-setup`) because a developer
verifying their own change is not independent verification (SOP Section 3).

## When to use
- A new developer is joining a Phoneme product team and needs their laptop set up.
- An existing developer is starting on a new Phoneme product and needs a second,
  independent environment for it.
- Someone asks "how do I set up my dev machine", "onboard me", or similar for a
  Phoneme product.

## Prerequisite
The product's Technical Stack Charter must already exist (`phoneme-technical-stack`
— for Teamora: `Technical/Teamora_Technical_Stack_Charter_v1.0.md`). Never guess a
runtime version or package manager; read it from the charter. If no charter exists
yet for this product, run `phoneme-technical-stack` first.

## Run the script first
`Deployment/Machine1_Env_Setup.ps1` is the actual mechanism for this checklist's
tooling steps (1, and reporting on 3/6) — an unattended, resumable, self-elevating
script, not a list of commands to type by hand. Have the developer run it from an
ordinary (non-admin) PowerShell in the repo's `Deployment/` folder:
```powershell
powershell -ExecutionPolicy Bypass -File .\Machine1_Env_Setup.ps1
```
It self-elevates (one UAC prompt) when a step needs admin rights, installs the
pinned Node.js (via nvm-windows) and Python, WSL2 + Docker Desktop (auto-rebooting
and resuming itself if Windows requires a restart), GitHub CLI, and the PostgreSQL
client — and reports (never fabricates) whether the repo's dependency lockfiles,
`.env.example`, and pre-commit config exist yet to run steps 3–6 against. Full
mechanics, flags, and what's deliberately left manual (git identity, SSH key
registration) are in `Deployment/MACHINE_A_SETUP_PROCESS.md` — read that before
walking a developer through this by hand. Re-running the script is always safe;
it resumes from `Deployment/machine1-setup-logs/state.json` instead of redoing
finished steps.

Steps 3–6 below only become runnable once the product's Phase 2 application
scaffold (lockfiles, `.env.example`, pre-commit config, build/test scripts) has
actually landed in the repo — that's separate development-stage work owned by
whoever scaffolds the product, not part of environment setup. The script reports
this status; it does not generate the scaffold itself.

## Checklist (SOP Section 8.1, in order)
1. **Runtime** — install the exact language runtime/package manager version pinned
   in the Technical Stack Charter. Never "whatever is newest." (Teamora: Node.js
   20.x + npm for NestJS/React services, Python 3.12 + pip for FastAPI services —
   confirm which service(s) this developer is assigned before picking.) Automated
   by the script above.
2. **Git & GitHub access** — configure git identity (`user.name`/`user.email`
   matching their Phoneme email), add their SSH key to GitHub, clone the product
   repository. Deliberately manual — the script only reports SSH key presence,
   never generates or registers one; this is a personal-identity/security-trust
   decision for the developer to make, not to inherit from a script default.
3. **Dependencies** — install from the committed lockfile only (`npm ci`, not
   `npm install`; `pip install -r requirements.txt` pinned, not a fresh resolve).
   An unpinned install can silently drift from what CI and staging actually run.
   Requires the Phase 2 scaffold (see above) — the script reports whether it's
   present, not automated further here.
4. **Local secrets** — copy `.env.example` to a local `.env` with dev-safe
   placeholder values. Real staging/production secrets are never copied onto a
   developer machine — those live only in Coolify's environment-variable store
   (`Deployment/ci-cd/COOLIFY_SETUP.md` Section 4/5).
5. **Pre-commit hooks** — install and enable the repo's lint/format hooks so
   style issues are caught before a PR, not in review.
6. **Clean baseline run** — run the full local build and unit test suite once,
   clean, *before* starting any feature work. This confirms the environment
   itself is sound before any future test failure gets blamed on code.
7. **Branch & REQ-ID discipline** — before the first commit, confirm:
   - Branch naming (SOP Section 4.1): `feature/REQ-<product>-<id>-<short-slug>`,
     e.g. `feature/REQ-TMR-14-jd-scoring-matrix`.
   - The REQ-ID (from the BRD/PRD, via `phoneme-brd-prd`) this session's work
     implements. Every commit and PR title references it. REQ-IDs are never
     renumbered — a changed requirement gets a new ID noting the old one.
   - Staging (`staging`) is the always-deployable integration branch; `main` is
     only ever updated by the CI/CD pipeline promoting a signed-off staging
     build (SOP Section 4.1) — never by a direct developer merge.

## What happens after setup
Developer implements the REQ-ID on the feature branch, runs local build/unit
tests, opens a PR tagged with the REQ-ID, a Reviewer checks it against the
linked requirement, and it merges to `staging` — which auto-deploys via
`Deployment/ci-cd/staging-deploy.yml` (or `-python.yml`) to the Coolify Staging
application. QA on Machine B takes it from there (`phoneme-qa-machine-setup`).

## Workflow
1. Confirm which Phoneme product and which service(s) within it (per the
   Technical Stack Charter) this developer will work on.
2. Have them run `Deployment/Machine1_Env_Setup.ps1` (see "Run the script
   first" above) — it covers step 1 and reports status on steps 3/6. Walk the
   remaining checklist items in order around it; don't skip to dependencies
   before git access is confirmed, since later steps assume the repo is
   already cloned.
3. Verify step 6 (clean baseline build+test) actually passes before declaring
   setup complete — a red baseline means the environment isn't ready, not that
   it's "close enough." Re-run the script any time to re-check tooling status;
   it resumes from its saved state rather than redoing finished steps.
4. Point them to the SOP's escalation procedure (Section 9) and their assigned
   Reviewer/Release Owner for questions about a specific requirement.
