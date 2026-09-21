# Machine B Setup — Unattended, Resumable Process

Companion to `Phoneme_SDLC_SOP_v1.2.docx` Section 8.2 and
`Deployment/MachineB_Env_Setup.ps1`. Same role as `MACHINE_A_SETUP_PROCESS.md`
plays for Section 8.1 — the as-built writeup of how the checklist actually
gets executed, not a list of commands typed by hand. Read that document
first if you haven't; this one only covers what's different for Machine B.

## Why Machine B is a lighter script than Machine A's

Section 2's environment topology keeps Machine A (development) and Machine B
(QA) deliberately separate: a developer verifying their own change isn't
independent verification. Machine B never runs the application locally at
all — it tests the *deployed staging build* over the network, against the
*frozen requirement text* (SOP Section 3). That means it needs none of
Machine A's Docker/WSL2/PostgreSQL/Redis stack — only a test runner
(Playwright) able to reach a remote staging URL. Nothing in Machine B's
checklist enables a Windows feature that forces a reboot, so there's no
auto-reboot/resume machinery here — `Machine1_Env_Setup.ps1` needed it for
WSL2; this script doesn't.

## Running it

From an **ordinary** (non-admin) PowerShell, inside the product repo's
`Deployment/` folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\MachineB_Env_Setup.ps1
```

Same self-elevation behavior as Machine A's script — it detects it isn't
elevated and relaunches itself (one UAC prompt) before any admin-only step.

Once the Release Owner has confirmed this product's actual staging URL, pass
it to get a real reachability check instead of just a reminder:

```powershell
powershell -ExecutionPolicy Bypass -File .\MachineB_Env_Setup.ps1 -StagingUrl https://staging.teamora.example.com
```

| Flag | Effect |
|---|---|
| `-NoElevate` | Report-only pass. |
| `-DryRun` | Report-only, and never runs an installer even for non-admin steps. |
| `-SkipNodeInstall` / `-SkipPlaywrightInstall` | Skip that one step. |
| `-StagingUrl <url>` | Test reachability to the given staging URL on port 443. |

## What gets automated vs. what stays manual, and why

**Automated:**
- Node.js — installed as a **baseline LTS**, not a pinned version, because
  nothing in the repo pins one for QA yet (that lands with the Phase 2 QA
  scaffold). Re-run the script once a version is pinned to confirm the
  baseline still matches, same discipline `Machine1_Env_Setup.ps1` applies
  to `.nvmrc`.
- Playwright + browser binaries — **only** once an actual
  `@playwright/test` version is found committed somewhere in the repo (the
  script scans every `package.json` in the tree for it). Until then it
  reports "pending Phase 2 QA scaffold," the same way Machine A's script
  never guesses an unpinned tool version.
- A reachability check against `-StagingUrl`, if given.
- `winget` self-bootstrap (best-effort — see `MACHINE_A_SETUP_PROCESS.md`'s
  section on this; the caveat and fallback are identical here).

**Deliberately not automated, and why:**
- **Network isolation to staging-only** (SOP 8.2: "Machine B never needs,
  and should never be given, production credentials or a route to the
  production database"). This is a network/IT-level control — firewall
  rules, VPN scoping, DNS — not something a PowerShell script running as
  the QA engineer can enforce on itself. The script only checks and
  reminds; get this confirmed with your network owner.
- **Dedicated QA test accounts.** Requires the product to actually be
  running, and is provisioned by whoever owns the product's user accounts —
  never fabricated by a setup script, and never real customer/candidate
  data (SOP 8.2).
- **Zephyr Scale / Jira login.** Account-level, owner/IT-provisioned, and
  must be QA's *own* login — test executions are recorded under the QA
  engineer's identity, never the developer's (SOP 8.2).
- **The sign-off report export and `git tag` itself** (SOP 8.6). The script
  only confirms the `Quality Assurance/` folder exists as the landing spot
  — the actual export/tag is a per-release action at the Test Sign-off
  Gate, not a one-time environment-setup step.

## Adapting this for a new Phoneme product

1. Copy `Deployment/MachineB_Env_Setup.ps1` into the new product repo's own
   `Deployment/` folder alongside its `Machine1_Env_Setup.ps1`.
2. Step 2's Playwright-pin scan already searches the whole repo tree
   generically — nothing to edit there.
3. Nothing else in the script is product-specific; only the `-StagingUrl`
   example in its header comment is worth updating once that product's
   Release Owner confirms its domain.

## Log locations

- Console transcript per run: `Deployment/machineb-setup-logs/machineb_env_setup_<timestamp>.log`
- Persistent resumable state: `Deployment/machineb-setup-logs/state.json`

Both gitignored (`Deployment/machineb-setup-logs/` in `.gitignore`), same
convention as Machine A's `machine1-setup-logs/`.
