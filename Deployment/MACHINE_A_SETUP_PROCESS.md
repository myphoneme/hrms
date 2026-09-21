# Machine A Setup — Unattended, Resumable Process

Companion to `Phoneme_SDLC_SOP_v1.2.docx` Section 8.1 and
`Deployment/Machine1_Env_Setup.ps1`. This document is to Section 8.1 what
`ci-cd/COOLIFY_SETUP.md` is to Sections 8.3–8.5: the as-built, practical
writeup of how the SOP's checklist actually gets executed, as opposed to a
list of commands a developer types by hand.

## Why this exists

Section 8.1 reads as a manual checklist (install the pinned runtime,
configure git, install dependencies, copy `.env.example`, enable pre-commit
hooks, run a clean build). Typed by hand, on every machine, for every
Phoneme product, that checklist drifts — a step gets skipped, a wrong
version gets installed, nobody remembers which machine reached which step
before a reboot interrupted it. `Machine1_Env_Setup.ps1` turns the checklist
into a single, idempotent, resumable script instead, so "set up Machine A"
means one command, on any machine, for any product.

## Running it

From an **ordinary** (non-admin) PowerShell, inside the product repo's
`Deployment/` folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\Machine1_Env_Setup.ps1
```

Do not open an elevated shell first — the script detects it isn't elevated
and relaunches itself elevated (one UAC prompt to approve). That self-
elevation is the point: a coder should never need to know or remember which
steps require admin rights.

Useful flags:

| Flag | Effect |
|---|---|
| `-NoElevate` | Report-only pass. Never relaunches elevated, never installs/enables/reboots anything admin-only. Good for "what's my status" without touching the system. |
| `-DryRun` | Like `-NoElevate`, and additionally never runs an installer for non-admin steps either. Use this to preview what a run would do. |
| `-NoAutoReboot` | Still enables WSL2's Windows features, but stops and waits for a manual reboot instead of restarting automatically. |
| `-SkipNodePin` / `-SkipWsl` / `-SkipDockerInstall` / `-SkipGitHubCliInstall` / `-SkipPostgresInstall` | Skip one specific step (e.g. a machine that already has Docker via another route). |
| `-Resume` | Set automatically by the script's own RunOnce registration before an auto-reboot. Not something you pass by hand. |

## What "resumable" actually means here

Every step's outcome is written to `Deployment/machine1-setup-logs/state.json`
(gitignored) as it completes. Re-running the script — for any reason, at any
time — re-reads that file and continues from there instead of starting over.

This matters specifically for WSL2: enabling its Windows features requires a
restart before Docker Desktop can be installed on top of it. Instead of the
script printing "now reboot, then remember to re-run me," it:

1. Registers itself under `HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce`
   with a command that re-invokes the exact same script with `-Resume`.
2. Logs the reason, waits 20 seconds (Ctrl+C to cancel — save your work), and
   calls `Restart-Computer -Force`.
3. At the next interactive logon, Windows itself fires the RunOnce entry —
   no one needs to remember to reopen a terminal.
4. The resumed run sees WSL2 now working, marks that step done, removes its
   own RunOnce entry, and continues to Docker Desktop, GitHub CLI, etc.

A safety cap (`-MaxAutoReboots`, default 2) stops this from looping forever
if something about the environment prevents WSL2 from ever reporting ready
— the script stops and asks for one manual reboot-and-rerun instead.

## What gets automated vs. what stays manual, and why

**Automated** (via `winget`, idempotent, safe to re-run):
Node.js pinned to the repo's `.nvmrc` (via `nvm-windows`), Python 3.12 if
entirely missing, WSL2's Windows features, Docker Desktop, GitHub CLI,
PostgreSQL 18 client, and pre-pulling the `redis:7` image once Docker
responds (there's no supported native Windows `redis-cli`, so local Redis
work goes through `docker run --rm -it redis:7 redis-cli ...` instead).

**Deliberately not automated:**
- **Git identity (`user.name`/`user.email`) and SSH key generation/GitHub
  registration.** These are personal-identity and security-trust decisions
  that differ per developer, and no setup script should be silently picking
  a name/email or deciding a key is trustworthy. On *this* machine there's
  an additional, harder reason: a ransomware incident was found and cleaned
  from `~/.ssh` and `C:\Program Files\PostgreSQL\18\bin` on 2026-09-21 (see
  `MACHINE1_READINESS.md`) — no key gets registered with GitHub here until
  security has cleared the machine.
- **Docker Desktop's first-run license acceptance.** `winget` installs the
  application silently, but its own first-launch EULA is a GUI dialog with
  no supported silent-accept flag. Open it once from the Start Menu after
  the script finishes; this is a genuine Windows/Docker Desktop limitation,
  not something the script skipped.
- **The application scaffold itself** (`package.json`, lockfiles,
  `.env.example`, pre-commit config, `docker-compose.yml`, build/test
  scripts). This is Phase 2 product work — it depends on BRD/PRD/Tech
  Design sign-off and the first REQ-ID being selected, not on anything a
  machine-setup script can install. The script reports this status clearly
  rather than pretending it's a tooling gap.

## `winget` on Windows Server

Unlike Windows 10/11, Windows Server does not ship `winget` preinstalled —
everything above that depends on it will report `blocked` until it's
available. The script makes one best-effort automatic attempt (downloading
and side-loading the App Installer bundle from the official
`microsoft/winget-cli` GitHub releases). This commonly fails on Server on
its own because App Installer also needs the `Microsoft.VCLibs` and
`Microsoft.UI.Xaml` dependency packages present, which the one-shot bundle
install doesn't chase down.

If Step 0 reports `winget` still unavailable, install it manually following
Microsoft's current "Install winget on Windows Server" guidance (search that
exact phrase — the dependency package links change often enough that hard-
coding them here would go stale), then re-run this script; everything downstream
picks up automatically once `winget` is present.

## Adapting this for a new Phoneme product

1. Copy `Deployment/Machine1_Env_Setup.ps1` into the new product repo's own
   `Deployment/` folder (rename if you like — nothing in it is hardcoded to
   a filename).
2. Steps 1–2 and 8–9 are already generic: they read *that* repo's own
   `.nvmrc` and scan *that* repo's own tree for a scaffold. No edits needed.
3. Step 7's "refuse to install over a prior PostgreSQL directory" guard is
   specific to this machine's 2026-06-07 incident. On a clean machine it's a
   harmless extra safety check (it just won't ever trigger); leave it in
   unless you have a specific reason to remove it.
4. Copy this document alongside it and update the product name in the
   header — the process itself doesn't change per product.
5. When the SOP itself next revises (v1.3+), reference this document the
   same way v1.2 added Appendix A for the Coolify walkthrough, so Section
   8.1 points at the as-built process rather than only the checklist prose.

## Log locations

- Console transcript per run: `Deployment/machine1-setup-logs/machine1_env_setup_<timestamp>.log`
- Persistent resumable state: `Deployment/machine1-setup-logs/state.json`

Both are gitignored (`Deployment/machine1-setup-logs/` in `.gitignore`) —
they're machine-local run artifacts, not something that belongs in the repo
history.
