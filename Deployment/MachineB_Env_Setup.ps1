<#
Phoneme SDLC SOP Section 8.2 -- Machine B QA/Test Environment Setup
(Reference implementation: Teamora / HR Management. Reusable per-product --
see the "REUSING THIS SCRIPT" note below.)

Companion to Deployment/Machine1_Env_Setup.ps1 (Machine A / developer setup,
SOP Section 8.1). Machine B is deliberately a much lighter environment: QA
never runs the application locally -- it tests the *deployed staging build*
over the network, against the *frozen requirement text*, never the
developer's local branch (SOP Section 3). So this script installs no
Docker/WSL/Postgres/Redis at all -- only what's needed to run the test
framework itself against a remote staging URL.

Same unattended/resumable design as Machine1_Env_Setup.ps1: run one command,
it self-elevates when a step needs admin rights, and re-running it any time
is always safe -- it re-reads Deployment/machineb-setup-logs/state.json and
only does what isn't already done. Unlike Machine A, nothing in this
checklist requires a Windows feature that forces a reboot, so there is no
auto-reboot/resume machinery here -- it isn't needed.

HOW TO RUN THIS:
  From an ORDINARY (non-admin) PowerShell, in the Deployment/ folder:
    powershell -ExecutionPolicy Bypass -File .\MachineB_Env_Setup.ps1
  Pass -StagingUrl <url> once the Release Owner has confirmed the product's
  staging URL, to have the script verify this machine can actually reach it:
    powershell -ExecutionPolicy Bypass -File .\MachineB_Env_Setup.ps1 -StagingUrl https://staging.teamora.example.com

  Flags:
    -NoElevate               Report-only pass; never relaunches elevated,
                              never installs anything admin-only.
    -DryRun                  Like -NoElevate, and never runs an installer
                              for non-admin steps either.
    -SkipNodeInstall          Skip the Node.js baseline install step.
    -SkipPlaywrightInstall    Skip the Playwright install step.
    -StagingUrl <url>         Test reachability to this URL (see above).

WHAT THIS AUTOMATES (maps to SOP v1.2 Section 8.2):
  1. Node.js runtime -- a QA-owned install, independent of whatever Machine A
     has (SOP 8.2 keeps the two machines' tooling separate). No version is
     pinned in this repo yet (that lands with the Phase 2 QA scaffold), so
     this installs the latest LTS as a working baseline, clearly flagged as
     provisional -- never guesses a specific pinned version that doesn't
     exist yet.
  2. Playwright (`@playwright/test`) + its browser binaries -- ONLY once a
     version is actually pinned somewhere in the repo (a `package.json`
     under, e.g., a future `qa/` or `e2e/` folder). Until then this reports
     "pending Phase 2 QA scaffold" rather than guessing a version to install,
     same discipline Machine1_Env_Setup.ps1 applies to Node/.nvmrc.
  3. Network reachability check to the staging URL, IF you pass -StagingUrl
     (the URL itself isn't fixed in the repo yet -- Technical Stack Charter
     row 6 marks the staging domain pattern "TBD, confirm with Release
     Owner"). Also prints the standing reminder that this machine must never
     be given production credentials or a network route to the production
     database -- that's a network/IT-level control this script cannot itself
     enforce, only remind about.
  4. Checks that the repo's `Quality Assurance/` folder exists, as the
     landing place for signed-off test-cycle reports (SOP 8.6).
  5. Bootstraps `winget` itself if missing (best-effort, same as Machine A --
     Windows Server doesn't ship it).

WHAT STAYS MANUAL, AND WHY (this script only reports these, never automates
them -- see Deployment/MACHINE_B_SETUP_PROCESS.md for the full writeup):
  - Dedicated QA test accounts for exercising the staging build (SOP 8.2) --
    these require the product to actually be running, and are provisioned
    by whoever owns the product's user accounts, never fabricated by a
    machine-setup script, and never real customer/candidate data.
  - Zephyr Scale / Jira login (SOP 8.2) -- QA's own account, an owner-
    performed step, recorded under the QA engineer's own identity so test
    executions are never attributed to a developer.
  - The actual sign-off report export and `git tag` at release time (SOP
    8.6) -- a per-release action at the Test Sign-off Gate, not a one-time
    environment-setup step.

REUSING THIS SCRIPT FOR A NEW PHONEME PRODUCT:
  Copy this file into the new repo's Deployment/ folder alongside its own
  Machine1_Env_Setup.ps1. Step 2's Playwright-pin search already scans the
  whole repo tree generically -- no per-product edits needed there. Update
  only the -StagingUrl example in this header comment once that product's
  Release Owner confirms its domain.

LOGGING & STATE:
  Console transcript per run: Deployment/machineb-setup-logs/machineb_env_setup_<timestamp>.log
  Resumable state: Deployment/machineb-setup-logs/state.json
  Both gitignored -- machine-local run artifacts, same convention as
  Machine1_Env_Setup.ps1's machine1-setup-logs/.
#>

[CmdletBinding()]
param(
  [switch]$NoElevate,
  [switch]$DryRun,
  [switch]$SkipNodeInstall,
  [switch]$SkipPlaywrightInstall,
  [string]$StagingUrl
)

# ---------------------------------------------------------------------------
# Paths (safe to compute before any elevation/logging decisions).
# ---------------------------------------------------------------------------
$ScriptPath = $MyInvocation.MyCommand.Path
$ScriptDir  = Split-Path -Parent $ScriptPath
$RepoRoot   = Split-Path -Parent $ScriptDir
$LogDir     = Join-Path $ScriptDir "machineb-setup-logs"
if (-not (Test-Path $LogDir)) {
  New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}
$StateFile = Join-Path $LogDir "state.json"

$IsElevated = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

# ---------------------------------------------------------------------------
# Step 0: self-elevate if needed, BEFORE opening a transcript in this
# (about-to-exit) process, so only the elevated process's run gets logged.
# ---------------------------------------------------------------------------
if (-not $IsElevated -and -not $NoElevate -and -not $DryRun) {
  $passthrough = New-Object System.Collections.Generic.List[string]
  $passthrough.Add('-NoProfile'); $passthrough.Add('-ExecutionPolicy'); $passthrough.Add('Bypass')
  $passthrough.Add('-File'); $passthrough.Add('"' + $ScriptPath + '"')
  if ($SkipNodeInstall)       { $passthrough.Add('-SkipNodeInstall') }
  if ($SkipPlaywrightInstall) { $passthrough.Add('-SkipPlaywrightInstall') }
  if ($StagingUrl)            { $passthrough.Add('-StagingUrl'); $passthrough.Add('"' + $StagingUrl + '"') }

  Write-Host "Not running elevated. Requesting admin rights now (a UAC prompt will appear) --" -ForegroundColor Yellow
  Write-Host "approve it to continue; this window will exit and a new elevated one will take over." -ForegroundColor Yellow
  Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList ($passthrough -join ' ')
  exit 0
}

# ---------------------------------------------------------------------------
# Logging: mirror all console output to a timestamped log file, same
# convention as Machine1_Env_Setup.ps1 and ci-cd/staging_server_setup.sh.
# ---------------------------------------------------------------------------
$RunStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$LogFile = Join-Path $LogDir "machineb_env_setup_$RunStamp.log"
Start-Transcript -Path $LogFile -Append | Out-Null

function Write-Step  { param([string]$Text) Write-Host ""; Write-Host "== $Text ==" -ForegroundColor Cyan }
function Write-Ok    { param([string]$Text) Write-Host "  [OK] $Text" -ForegroundColor Green }
function Write-Warn2 { param([string]$Text) Write-Host "  [ACTION NEEDED] $Text" -ForegroundColor Yellow }
function Write-Skip  { param([string]$Text) Write-Host "  [SKIP] $Text" -ForegroundColor DarkGray }
function Test-CommandExists { param([string]$Name) return [bool](Get-Command $Name -ErrorAction SilentlyContinue) }

function Test-WingetWorks {
  # A sideloaded App Installer package can be present on PATH but still
  # throw "No applicable app licenses found" when actually invoked (see
  # Step 0) -- Get-Command alone can't tell working from broken, so this
  # actually runs it and checks the exit code (via cmd /c, per the same
  # PowerShell 5.1 native-stderr-redirection caveat used elsewhere here).
  if (-not (Test-CommandExists "winget")) { return $false }
  $null = cmd /c "winget --version" 2>&1
  return ($LASTEXITCODE -eq 0)
}

function Update-SessionPath {
  $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
  $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
  $env:PATH = "$machinePath;$userPath"
}

# ---------------------------------------------------------------------------
# State: small JSON file under machineb-setup-logs/, same idempotency
# convention as Machine1_Env_Setup.ps1 -- re-running always safe.
# ---------------------------------------------------------------------------
function Get-State {
  if (Test-Path $StateFile) {
    try { return (Get-Content $StateFile -Raw | ConvertFrom-Json) } catch { }
  }
  return [PSCustomObject]@{
    version   = 1
    createdAt = (Get-Date -Format o)
    updatedAt = (Get-Date -Format o)
    steps     = [PSCustomObject]@{
      winget     = "not-started"
      node       = "not-started"
      playwright = "not-started"
      qa_folder  = "not-started"
    }
  }
}

function Save-State {
  param($State)
  $State.updatedAt = Get-Date -Format o
  try {
    $State | ConvertTo-Json -Depth 5 | Set-Content -Path $StateFile -Encoding UTF8 -ErrorAction Stop
  } catch {
    # Never let a locked/inaccessible state file crash the whole run --
    # resumability degrades to "re-check everything next time," which is
    # safe (every step re-verifies live state), just not as fast.
    Write-Host "  [WARN] Could not write state file ($StateFile): $($_.Exception.Message) -- continuing without saving this step's status." -ForegroundColor Yellow
  }
}

function Set-StepStatus {
  param($State, [string]$Step, [string]$Status)
  $State.steps.$Step = $Status
  Save-State $State
}

$State = Get-State

function Install-ViaWinget {
  param([string]$Id, [string]$FriendlyName, [string]$CheckCommand)
  if (Test-CommandExists $CheckCommand) {
    Write-Ok "$FriendlyName already installed."
    return $true
  }
  if ($DryRun) {
    Write-Skip "DryRun -- would install $FriendlyName via winget (id: $Id)."
    return $false
  }
  if (-not (Test-CommandExists "winget")) {
    Write-Warn2 "winget not available -- cannot auto-install $FriendlyName. See MACHINE_B_SETUP_PROCESS.md / MACHINE_A_SETUP_PROCESS.md for the manual winget bootstrap on Windows Server."
    return $false
  }
  Write-Host "  Installing $FriendlyName via winget (id: $Id)..."
  try {
    winget install -e --id $Id --accept-source-agreements --accept-package-agreements --silent | Out-Null
  } catch {
    Write-Warn2 "$FriendlyName install via winget threw: $($_.Exception.Message)"
    return $false
  }
  Update-SessionPath
  if (Test-CommandExists $CheckCommand) {
    Write-Ok "$FriendlyName installed."
    return $true
  }
  Write-Warn2 "$FriendlyName install ran but '$CheckCommand' still isn't detected in this session -- it may need a fresh shell; re-run this script to confirm."
  return $false
}

function Find-PlaywrightPin {
  # Looks for an actual committed @playwright/test version anywhere in the
  # repo (e.g. a future qa/ or e2e/ package.json). Returns $null if none
  # exists yet -- never guesses a version to install instead.
  $candidates = Get-ChildItem -Path $RepoRoot -Recurse -Filter "package.json" -ErrorAction SilentlyContinue -File |
    Where-Object { $_.FullName -notmatch "\\node_modules\\|\\\.tools\\" }
  foreach ($c in $candidates) {
    try {
      $json = Get-Content $c.FullName -Raw | ConvertFrom-Json
      $ver = $null
      if ($json.devDependencies -and $json.devDependencies.'@playwright/test') { $ver = $json.devDependencies.'@playwright/test' }
      elseif ($json.dependencies -and $json.dependencies.'@playwright/test') { $ver = $json.dependencies.'@playwright/test' }
      if ($ver) { return [PSCustomObject]@{ File = $c.FullName; Version = $ver } }
    } catch { }
  }
  return $null
}

Write-Host "Run log: $LogFile"
Write-Host "State file: $StateFile"
Write-Host "Run started: $(Get-Date -Format o)"
Write-Host "Elevated session: $IsElevated"

# ---------------------------------------------------------------------------
Write-Step "Step 0: winget availability"
if (Test-WingetWorks) {
  Set-StepStatus $State "winget" "done"
  Write-Ok "winget is available and working."
} elseif ($DryRun) {
  Write-Skip "DryRun -- not attempting winget bootstrap."
} else {
  if (Test-CommandExists "winget") {
    Write-Warn2 "winget.exe is present but not functional (typically 'No applicable app licenses found' -- a sideloaded install outside the Microsoft Store, which Windows Server doesn't have, has no license entitlement). Re-provisioning it with its offline license..."
  } else {
    Write-Warn2 "winget not found (expected on Windows Server). Bootstrapping it..."
  }
  try {
    $ProgressPreference = 'SilentlyContinue'
    Write-Host "  Querying the latest winget-cli release from GitHub..."
    $Release = Invoke-RestMethod -Uri "https://api.github.com/repos/microsoft/winget-cli/releases/latest" -Headers @{ "User-Agent" = "PhonemeMachineBSetup" } -TimeoutSec 30
    $BundleAsset  = $Release.assets | Where-Object { $_.name -like "*.msixbundle" } | Select-Object -First 1
    $DepsAsset    = $Release.assets | Where-Object { $_.name -like "*Dependencies*.zip" } | Select-Object -First 1
    $LicenseAsset = $Release.assets | Where-Object { $_.name -like "*License*.xml" } | Select-Object -First 1
    if (-not $BundleAsset) { throw "Could not find a .msixbundle asset on the latest winget-cli GitHub release." }

    $BootstrapDir = Join-Path $env:TEMP "phoneme-winget-bootstrap"
    if (Test-Path $BootstrapDir) { Remove-Item $BootstrapDir -Recurse -Force }
    New-Item -ItemType Directory -Path $BootstrapDir -Force | Out-Null

    $BundlePath = Join-Path $BootstrapDir $BundleAsset.name
    Write-Host "  Downloading $($BundleAsset.name)..."
    Invoke-WebRequest -Uri $BundleAsset.browser_download_url -OutFile $BundlePath -UseBasicParsing -TimeoutSec 60

    $DepPaths = @()
    if ($DepsAsset) {
      $DepsZip = Join-Path $BootstrapDir $DepsAsset.name
      Write-Host "  Downloading dependency packages ($($DepsAsset.name))..."
      Invoke-WebRequest -Uri $DepsAsset.browser_download_url -OutFile $DepsZip -UseBasicParsing -TimeoutSec 60
      $DepsDir = Join-Path $BootstrapDir "deps"
      Expand-Archive -Path $DepsZip -DestinationPath $DepsDir -Force
      $DepPaths = @(Get-ChildItem -Path $DepsDir -Recurse -Filter "*.appx" | Where-Object { $_.FullName -match "\\x64\\" } | Select-Object -ExpandProperty FullName)
    }

    $LicensePath = $null
    if ($LicenseAsset) {
      $LicensePath = Join-Path $BootstrapDir $LicenseAsset.name
      Write-Host "  Downloading offline license ($($LicenseAsset.name))..."
      Invoke-WebRequest -Uri $LicenseAsset.browser_download_url -OutFile $LicensePath -UseBasicParsing -TimeoutSec 60
    }

    if (Get-Command Add-AppxProvisionedPackage -ErrorAction SilentlyContinue) {
      Write-Host "  Provisioning winget via DISM (online, with dependencies + offline license)..."
      $DismArgs = @{ Online = $true; PackagePath = $BundlePath; ErrorAction = 'Stop' }
      if ($DepPaths.Count -gt 0) { $DismArgs.DependencyPackagePath = $DepPaths }
      if ($LicensePath) { $DismArgs.LicensePath = $LicensePath }
      Add-AppxProvisionedPackage @DismArgs | Out-Null
    } else {
      Write-Warn2 "Add-AppxProvisionedPackage (DISM) isn't available on this system -- falling back to a per-user Add-AppxPackage install, which may still hit the licensing issue on Windows Server."
      if ($DepPaths.Count -gt 0) {
        Add-AppxPackage -Path $BundlePath -DependencyPath $DepPaths -ErrorAction Stop
      } else {
        Add-AppxPackage -Path $BundlePath -ErrorAction Stop
      }
    }
    Update-SessionPath
  } catch {
    Write-Warn2 "Automatic winget bootstrap failed: $($_.Exception.Message)"
    Write-Warn2 "Common causes on Windows Server: no outbound HTTPS path to github.com/api.github.com (corporate proxy/firewall -- this script does not read a proxy config), or this step not running elevated (DISM provisioning needs admin). See MACHINE_A_SETUP_PROCESS.md for the manual fallback."
  }
  if (Test-WingetWorks) {
    Set-StepStatus $State "winget" "done"
    Write-Ok "winget bootstrapped and confirmed working."
  } else {
    Write-Warn2 "winget still not functional after bootstrap -- see MACHINE_A_SETUP_PROCESS.md for the manual fallback. Steps below that depend on it will report blocked until resolved."
  }
}

# ---------------------------------------------------------------------------
Write-Step "Step 1: Node.js runtime (for the Playwright/test-runner tooling, independent of Machine A)"
if ($SkipNodeInstall) {
  Write-Skip "Node install skipped (-SkipNodeInstall)."
} elseif (Test-CommandExists "node") {
  Write-Ok "Node found: $(node -v) (this machine's own install, per SOP 8.2)."
  Set-StepStatus $State "node" "done"
} else {
  Write-Warn2 "No Node.js found. No QA-specific version is pinned in the repo yet (Phase 2 QA scaffold pending) -- installing latest LTS as a working baseline."
  if (Install-ViaWinget -Id "OpenJS.NodeJS.LTS" -FriendlyName "Node.js LTS" -CheckCommand "node") {
    Set-StepStatus $State "node" "done"
    Write-Warn2 "Re-run this script once a QA scaffold pins an exact Node/Playwright version, to confirm this baseline still matches it."
  } else {
    Set-StepStatus $State "node" "blocked"
  }
}

# ---------------------------------------------------------------------------
Write-Step "Step 2: Test framework -- Playwright + browser binaries"
if ($SkipPlaywrightInstall) {
  Write-Skip "Playwright install skipped (-SkipPlaywrightInstall)."
} else {
  $Pin = Find-PlaywrightPin
  if (-not $Pin) {
    Write-Warn2 "No @playwright/test version pinned anywhere in the repo yet. This is Phase 2 QA scaffold work, not a tooling gap -- not installing an arbitrary version."
    Set-StepStatus $State "playwright" "blocked"
  } else {
    Write-Host "  Pin found in $($Pin.File): @playwright/test@$($Pin.Version)"
    if (-not (Test-CommandExists "npx")) {
      Write-Warn2 "npx not available yet -- if Node was just installed above, open a new session and re-run this script."
      Set-StepStatus $State "playwright" "blocked"
    } elseif ($DryRun) {
      Write-Skip "DryRun -- would run: npm install -g @playwright/test@$($Pin.Version); npx playwright install"
    } else {
      Write-Host "  Installing @playwright/test@$($Pin.Version) and its browser binaries..."
      npm install -g "@playwright/test@$($Pin.Version)" | Out-Null
      npx playwright install | Out-Null
      Set-StepStatus $State "playwright" "done"
      Write-Ok "Playwright $($Pin.Version) and browser binaries installed."
    }
  }
}

# ---------------------------------------------------------------------------
Write-Step "Step 3: Network scope -- staging only (SOP 8.2: never production)"
if ($StagingUrl) {
  try {
    $UriHost = ([uri]$StagingUrl).Host
    $Result = Test-NetConnection -ComputerName $UriHost -Port 443 -WarningAction SilentlyContinue
    if ($Result.TcpTestSucceeded) {
      Write-Ok "Staging URL host '$UriHost' is reachable on 443."
    } else {
      Write-Warn2 "Staging URL host '$UriHost' did NOT respond on 443 -- confirm the URL and network path with the Release Owner."
    }
  } catch {
    Write-Warn2 "Could not test '$StagingUrl': $($_.Exception.Message)"
  }
} else {
  Write-Warn2 "No -StagingUrl passed. Per the Technical Stack Charter, the staging domain pattern is still TBD -- confirm the exact URL with the Release Owner, then re-run with -StagingUrl <url> to verify reachability."
}
Write-Warn2 "This machine must never be given production credentials or a network route to the production database (SOP 8.2). That is a network/IT-level control this script cannot enforce -- confirm it with your network owner, not just by reading this message."

# ---------------------------------------------------------------------------
Write-Step "Step 4: Dedicated QA test accounts (manual, owner-provisioned)"
Write-Warn2 "Set up QA-owned test accounts for exercising the staging build once it exists. Never use real customer/candidate data (SOP 8.2). Not automatable -- the product has to be running, and account creation is an owner action."

# ---------------------------------------------------------------------------
Write-Step "Step 5: Test-management tool login (Zephyr Scale / Jira, manual)"
Write-Warn2 "Connect to Zephyr Scale (under the product's Jira project) with YOUR OWN QA login -- never the developer's. Account-level, owner/IT-provisioned, not something this script can do for you."

# ---------------------------------------------------------------------------
Write-Step "Step 6: Sign-off export path (SOP 8.6)"
$QaFolder = Join-Path $RepoRoot "Quality Assurance"
if (Test-Path $QaFolder) {
  Write-Ok "'Quality Assurance/' folder exists at: $QaFolder"
  Set-StepStatus $State "qa_folder" "done"
} else {
  Write-Warn2 "'Quality Assurance/' folder not found at the repo root -- confirm the convention before the first sign-off export."
  Set-StepStatus $State "qa_folder" "blocked"
}
Write-Host "  Reminder: at sign-off, export the release's test cycle from Zephyr Scale as TestReport_<product>_<release>_<date>.docx into that folder, commit it, and tag the certifying commit (e.g. git tag release-v2.4.0-qa-signoff). A superseding release gets its own dated report/tag -- never edit an existing one." -ForegroundColor Gray

# ---------------------------------------------------------------------------
Write-Step "Done -- current status"
$State = Get-State
foreach ($Key in $State.steps.PSObject.Properties.Name) {
  $Val = $State.steps.$Key
  switch ($Val) {
    "done"    { Write-Ok "$Key -- done" }
    "blocked" { Write-Warn2 "$Key -- blocked, see the step above" }
    default   { Write-Skip "$Key -- $Val" }
  }
}
Write-Host ""
Write-Host "Steps 4-5 (test accounts, Zephyr/Jira login) and the Step 6 export itself are owner/per-release actions -- always manual, not tracked in state.json." -ForegroundColor DarkGray
Write-Host ""
Write-Host "Full log of this run saved to: $LogFile"
Write-Host "State file (re-run any time -- it resumes from here): $StateFile"

Stop-Transcript | Out-Null
