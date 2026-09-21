---
name: phoneme-qa-machine-setup
description: Walk a QA engineer through setting up Machine B (an independent test environment) for a Phoneme product, per SOP Section 8.2 — so onboarding a new QA engineer follows the same checklist every time instead of drifting per person.
---

# Phoneme Machine B — QA/Test Environment Setup

Onboarding companion to `Phoneme_SDLC_SOP_v1.1.docx` Section 8.2. "Machine B" is
SOP terminology for an independent QA machine — deliberately separate from a
developer's Machine A (`phoneme-dev-machine-setup`), because QA verifies the
*deployed staging build* against the *frozen requirement text*, never the
developer's local branch or understanding of the requirement (SOP Section 3).

## When to use
- A new QA engineer is joining a Phoneme product team and needs their test
  machine set up.
- An existing QA engineer is starting coverage on a new Phoneme product.
- Someone asks "how do I set up my QA/test machine", "onboard me as QA", or
  similar for a Phoneme product.

## Prerequisite
The product's Technical Stack Charter must already exist (`phoneme-technical-stack`
— for Teamora: `Technical/Teamora_Technical_Stack_Charter_v1.0.md`) — it names the
test framework/runner to install. If no charter exists yet, run
`phoneme-technical-stack` first.

## Run the script first
`Deployment/MachineB_Env_Setup.ps1` is the actual mechanism for this checklist's
tooling steps (1, and reporting on 5) — an unattended, resumable, self-elevating
script, lighter than Machine A's since QA never runs the application locally, only
tests the deployed staging build over the network. Have the QA engineer run it
from an ordinary (non-admin) PowerShell in the repo's `Deployment/` folder:
```powershell
powershell -ExecutionPolicy Bypass -File .\MachineB_Env_Setup.ps1 -StagingUrl <staging-url-if-known>
```
It self-elevates (one UAC prompt) when a step needs admin rights, installs a
Node.js baseline and — once a version is actually pinned in the repo — Playwright
and its browser binaries, checks reachability to `-StagingUrl` if given, and
confirms the repo's `Quality Assurance/` folder exists for sign-off exports. It
never invents QA accounts, Zephyr/Jira logins, or network isolation rules — those
stay manual (see checklist items 2–4 below) and the script says so explicitly
rather than silently skipping them. Full mechanics and flags are in
`Deployment/MACHINE_B_SETUP_PROCESS.md` — read that before walking a QA engineer
through this by hand. Re-running the script is always safe; it resumes from
`Deployment/machineb-setup-logs/state.json` instead of redoing finished steps.

## Checklist (SOP Section 8.2, in order)
1. **Test framework** — install the test framework/runner specified in the
   Technical Stack Charter (e.g. Playwright) and its browser binaries. Kept
   independent of whatever Machine A has installed — QA's tooling is its own,
   not inherited from a developer's setup. Automated by the script above, once
   a version is pinned in the repo (Phase 2 QA scaffold — the script reports
   "pending" rather than guessing a version before then).
2. **Network scope — staging only** — configure network access to the staging
   URL only. Machine B never needs, and must never be given, production
   credentials or a route to the production database. The script can *check*
   reachability to a given staging URL, but the isolation itself is a
   network/IT-level control — deliberately manual, confirm with your network
   owner.
3. **Dedicated QA test accounts** — set up QA-owned test accounts for
   exercising the staging build. Never use real customer/candidate data.
   Deliberately manual — requires the product to be running and is an owner
   action, never fabricated by a script.
4. **Test-management tool** — connect to Zephyr Scale (under the product's
   Jira project) with QA's *own* login. Test executions are always recorded
   under the QA engineer's identity, never the developer's. Deliberately
   manual — account-level, owner/IT-provisioned.
5. **Sign-off export path** — confirm the local path/convention for exporting
   a signed-off test cycle's results (SOP Section 8.6) *before* the first
   execution of a release: export the release's test cycle from Zephyr Scale,
   generate a dated sign-off report (`TestReport_<product>_<release>_<date>.docx`)
   into the repo's `Quality Assurance/` folder, commit it, and tag the exact
   commit it certifies (e.g. `git tag release-v2.4.0-qa-signoff`). A superseding
   release gets its own dated report and tag — an existing sign-off report is
   never edited or overwritten after the fact. The script confirms the folder
   exists; the export/tag itself is a per-release action, not environment setup.

## What QA actually does with this setup
Pulls the deployed staging build (never the developer's local environment) at
the Coolify-issued staging URL, executes every test case (TC-ID) mapped to the
REQ-IDs newly present in that build. Each execution is recorded with a
pass/fail result and the build/commit hash it ran against; a failure logs a
defect referencing both the TC-ID and REQ-ID. A failed test case sends its
REQ-ID back to development as a fix task — same REQ-ID, since the requirement
itself hasn't changed. QA either signs off (Test Sign-off Gate, SOP Section
5.4) or bounces the release back to development; a REQ-ID failing twice
escalates to the Release Owner before a third attempt (SOP Section 9).

## Workflow
1. Confirm which Phoneme product this QA engineer covers, and get the current
   staging URL and Jira/Zephyr Scale project from the Release Owner.
2. Have them run `Deployment/MachineB_Env_Setup.ps1 -StagingUrl <url>` (see "Run
   the script first" above) once the staging URL is known — it covers step 1 and
   reports status on step 5. Walk the remaining (manual, account-level) checklist
   items — 2, 3, 4 — around it.
3. Have them execute one already-passing test case against the current staging
   build as a smoke check that the setup itself works, before assigning real
   release coverage.
4. Point them to the escalation procedure (SOP Section 9) and the Release Owner
   for anything ambiguous in a requirement's acceptance criteria.
