# Coolify Setup — Phoneme Self-Hosted Staging & Production

Companion to `Phoneme_SDLC_SOP_v1.1.docx` Section 8.3–8.5. This is the one-time
setup per product; the GitHub Actions workflows in this same folder
(`staging-deploy.yml`, `production-release.yml`) are what run on every commit
afterward.

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

Repo → **Settings → Secrets and variables → Actions**:

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

## 8. Fill in the workflow placeholders

Once this product's Technical Stack Charter is confirmed (`phoneme-technical-stack`),
replace the `<PLACEHOLDER>` lines in `staging-deploy.yml` and
`production-release.yml` with the real install/build/test commands for that
stack.

## Dashboard

Coolify's own dashboard (`http://<server-ip>:8000`, or your configured
domain) shows, per application, the currently deployed commit hash, deploy
history, and health-check status — this is the "what's live in staging vs.
production right now" view referenced in SOP Section 8.4. It does not track
requirement/test progress — that stays in Jira + Zephyr Scale (SOP Section 7).
