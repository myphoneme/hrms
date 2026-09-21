# Coolify Setup — Phoneme Self-Hosted Staging & Production

Companion to `Phoneme_SDLC_SOP_v1.1.docx` Section 8.3–8.5 and
`Technical/Teamora_Technical_Stack_Charter_v1.0.md`. This is the one-time setup
per **service** (Teamora is a microservices product per Tech Design §17 — Auth,
Notification, Requisition, Scoring Matrix, JD Generation, Resume Parsing,
Dedupe, plus the frontend — so steps 4–7 below happen once per service, not
once for the whole product). The GitHub Actions workflows in this same folder
(`staging-deploy.yml`/`staging-deploy-python.yml`,
`production-release.yml`/`production-release-python.yml`, picked by whether
the service is NestJS/TypeScript or Python/FastAPI) are what run on every
commit afterward.

## 1. Provision the server

Any VM/server on Phoneme's own infrastructure that can reach the internet
(to pull the GitHub repo and issue Let's Encrypt certificates) and that you
control root access to. A single small VM can host both the Staging and
Production applications for one product if traffic is light; separate VMs
are safer once a product has real customer traffic.

## 2. Install Coolify

On the server, as root:

```bash
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
```

This installs Coolify itself (it manages its own reverse proxy, SSL via
Let's Encrypt, and container runtime). Once finished, it prints the URL
(`http://<server-ip>:8000`) to open and finish setup (create the admin
account) from a browser.

## 3. Connect the GitHub repository

In the Coolify dashboard: **Sources → Add → GitHub** and authorize access to
the `hrms` repository (or whichever repo the product lives in). This lets
Coolify pull commits without you handing it a personal SSH key.

## 4. Create the Staging application

**Projects → New → Application**, select the repo, branch `staging`, and
the correct build pack for the product's Technical Stack Charter (Coolify
auto-detects Node/Python/Docker in most cases). Set:

- **Auto Deploy:** ON — this is what makes Section 8.3's "commit → staging
  redeploy" happen with no GitHub Actions step needed for staging's own
  redeploy trigger (the `staging-deploy.yml` workflow still runs the test
  suite first and calls the webhook so a broken build never even reaches
  Coolify's auto-deploy).
- **Environment variables:** set here, never committed to the repo.
- **Health check path:** point it at the product's health-check endpoint
  (SOP Section 8.3) so Coolify's own dashboard shows true pass/fail, not
  just "container started."

Under **Webhooks**, copy the deploy webhook URL — this becomes the GitHub
secret `COOLIFY_STAGING_WEBHOOK`.

## 5. Create the Production application

Same steps, branch `main`, but set **Auto Deploy: OFF** — production is
only ever redeployed by the `production-release.yml` GitHub Actions
workflow, after the regression suite and the Release Owner's approval both
pass (SOP Section 8.5). Copy its webhook URL into
`COOLIFY_PRODUCTION_WEBHOOK`, and note its rollback/redeploy-previous-build
webhook (Coolify keeps deployment history per application) into
`COOLIFY_PRODUCTION_ROLLBACK_WEBHOOK`.

## 6. Add the GitHub secrets

Repo → **Settings → Secrets and variables → Actions**. With one repo hosting
multiple services, suffix each secret with the service name once a second
service's workflow is added (e.g. `COOLIFY_STAGING_WEBHOOK_AUTH`,
`COOLIFY_STAGING_WEBHOOK_JD_GEN`) and update that service's workflow file to
match — the single unsuffixed names below are fine for the first service:

| Secret | Value |
|---|---|
| `COOLIFY_STAGING_WEBHOOK` | Staging application's deploy webhook URL |
| `COOLIFY_PRODUCTION_WEBHOOK` | Production application's deploy webhook URL |
| `COOLIFY_PRODUCTION_ROLLBACK_WEBHOOK` | Production application's redeploy-previous webhook URL |
| `PRODUCTION_SMOKE_URL` | Production's health-check endpoint, for the post-deploy smoke test |

## 7. Add the GitHub Environment approval gate

Repo → **Settings → Environments → New environment → `production`** → add
the Release Owner as a required reviewer. This is what makes
`production-release.yml`'s `environment: production` step actually pause
for a human go/no-go instead of deploying unattended.

## 8. Workflow commands are filled in — verify they match the real service

The Technical Stack Charter is confirmed (`Technical/Teamora_Technical_Stack_Charter_v1.0.md`),
so `staging-deploy.yml`/`production-release.yml` (NestJS/TypeScript + the React
frontend) and `staging-deploy-python.yml`/`production-release-python.yml`
(Python/FastAPI services) already have real install/lint/build/test commands
instead of placeholders. Before using either pair on an actual service repo,
confirm its `package.json` scripts (`build`, `test`, `test:regression`, `lint`)
or `requirements.txt`/pytest markers (`regression`) actually exist and match —
these commands are the charter's default convention, not yet verified against
committed code.

## Dashboard

Coolify's own dashboard (`http://<server-ip>:8000`, or your configured
domain) shows, per application, the currently deployed commit hash, deploy
history, and health-check status — this is the "what's live in staging vs.
production right now" view referenced in SOP Section 8.4. It does not track
requirement/test progress — that stays in Jira + Zephyr Scale (SOP Section 7).
