<#
Phoneme SDLC SOP Section 8.1 -- Machine A Developer Environment Setup
(Reference implementation: Teamora / HR Management. Reusable per-product --
see the "REUSING THIS SCRIPT" note below.)

This is an unattended, resumable provisioning script, not a one-shot list of
manual commands. It is meant to be the actual SOP-aligned process: a coder
on any machine runs ONE command, and the script self-elevates, installs what
it can, reboots itself when Windows requires it, and automatically resumes
after logon -- re-reading its own saved state -- until everything it can
automate is done.

HOW TO RUN THIS:
  From an ORDINARY (non-admin) PowerShell, in the Deployment/ folder:
    powershell -ExecutionPolicy Bypass -File .\Machine1_Env_Setup.ps1
  The script detects it is not elevated and relaunches itself elevated
  (one UAC prompt). Do not manually open an elevated shell first -- that
  extra step is exactly what this script exists to remove.

  Flags:
    -NoElevate            Report-only pass; never relaunch elevated, never
                           install/enable/reboot anything admin-only.
    -DryRun               Like -NoElevate, and additionally never runs any
                           installer even for non-admin steps.
    -NoAutoReboot          Enable the WSL2 features but stop and wait for you
                           to reboot manually instead of an automatic restart.
    -SkipNodePin / -SkipWsl / -SkipDockerInstall / -SkipGitHubCliInstall /
    -SkipPostgresInstall   Skip that one step.
    -Resume                Set automatically by the Windows RunOnce entry
                           this script registers before an automatic reboot;
                           you do not need to pass this yourself.

WHAT THIS AUTOMATES (maps to SOP v1.2 Section 8.1):
  1. Node.js runtime pinned to .nvmrc -- installs nvm-windows via winget if
     needed, then `nvm install`/`nvm use` to switch the active Node.
  2. Python runtime pinned to 3.12.x -- installs via winget only if Python
     is entirely missing (does not reorder PATH if a different version is
     already first on it -- see NOTE below).
  3. WSL2 (Microsoft-Windows-Subsystem-Linux + VirtualMachinePlatform
     Windows features) -- enables both via DISM, and if Windows reports a
     restart is required, registers a RunOnce resume entry and reboots
     automatically (20s cancel window), then continues on next logon.
  4. Docker Desktop -- installed via winget once WSL2 is confirmed working.
  5. GitHub CLI (`gh`) -- installed via winget.
  6. PostgreSQL 18 client -- installed via winget, UNLESS a prior
     C:\Program Files\PostgreSQL\18 directory is still present, in which
     case it refuses to install over it (see NOTE below).
  7. Once Docker responds, pre-pulls the `redis:7` image so
     `docker run --rm -it redis:7 redis-cli ...` works with no separate
     install (there is no official native Windows redis-cli).
  8. Reports repo scaffold status (package.json, .env.example, pre-commit
     config, requirements.txt/pyproject.toml) -- this is Phase 2 application
     work this script cannot generate, so it is reported, not automated.
  9. Bootstraps `winget` itself if missing (best-effort -- see NOTE below;
     Windows Server does not ship it, unlike Windows 10/11).

STATE & RESUMABILITY:
  Progress is persisted to Deployment/machine1-setup-logs/state.json after
  every step (gitignored). Re-running the script re-reads this file and
  skips whatever is already marked done, so it is always safe to re-run --
  including automatically, via the RunOnce registry entry this script sets
  under HKCU:\...\RunOnce before an auto-reboot, which is what makes the
  "restart in the middle of setup" case unattended instead of a manual
  "remember to re-run this after you log back in."
  Loop safety: at most 2 automatic reboots per run (see -MaxAutoReboots);
  beyond that the script stops and asks you to reboot manually once more.

LOGGING:
  Every run's full console output is captured via Start-Transcript to a
  timestamped log file under Deployment/machine1-setup-logs/, in addition
  to being shown on screen -- same convention as ci-cd/staging_server_setup.sh.

REUSING THIS SCRIPT FOR A NEW PHONEME PRODUCT:
  Copy this file into the new repo's Deployment/ folder. Steps 1-2, 7 and 8
  are already generic (they read that repo's own .nvmrc/scaffold). Step 6's
  "prior PostgreSQL install" guard is specific to this machine's 2026-06-07
  ransomware incident (see MACHINE1_READINESS.md) -- strip that guard on a
  clean machine, or leave it as a harmless extra safety check. See the
  companion doc Deployment/MACHINE_A_SETUP_PROCESS.md for the full writeup
  of this as a repeatable SOP process, including what remains a deliberate
  manual step and why.

NOTE -- things this script deliberately does NOT automate, and why:
  - Git identity (user.name/user.email) and SSH key generation/registration
    with GitHub: these are personal-identity and security-trust decisions
    that differ per developer and, on this machine specifically, are on
    hold pending security clearance of the 2026-06-07 ransomware incident
    (BlackHunt-pattern files were found and removed from ~/.ssh and
    C:\Program Files\PostgreSQL\18\bin). Reported only, never generated or
    registered automatically, on any machine.
  - Docker Desktop's first-run license acceptance: winget installs the
    application silently, but Docker Desktop's own first-launch EULA is a
    GUI dialog with no supported silent-accept flag -- open it once from
    the Start Menu after this script finishes.
  - winget itself is not preinstalled on Windows Server (unlike Windows
    10/11). Step 9 attempts the standard standalone-bundle bootstrap, but
    it commonly needs dependency packages (VCLibs, UI.Xaml) that are not
    reliably scriptable in one shot on Server -- if it fails, see the
    manual fallback in MACHINE_A_SETUP_PROCESS.md.
#>

[CmdletBinding()]
param(
  [switch]$Resume,
  [switch]$NoElevate,
  [switch]$NoAutoReboot,
  [switch]$DryRun,
  [switch]$SkipNodePin,
  [switch]$SkipWsl,
  [switch]$SkipDockerInstall,
  [switch]$SkipGitHubCliInstall,
  [switch]$SkipPostgresInstall,
  [int]$MaxAutoReboots = 2
)

# ---------------------------------------------------------------------------
# Paths (safe to compute before any elevation/logging decisions).
# ---------------------------------------------------------------------------
$ScriptPath = $MyInvocation.MyCommand.Path
$ScriptDir  = Split-Path -Parent $ScriptPath
$RepoRoot   = Split-Path -Parent $ScriptDir
$LogDir     = Join-Path $ScriptDir "machine1-setup-logs"
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
  if ($Resume)                { $passthrough.Add('-Resume') }
  if ($NoAutoReboot)          { $passthrough.Add('-NoAutoReboot') }
  if ($SkipNodePin)           { $passthrough.Add('-SkipNodePin') }
  if ($SkipWsl)                { $passthrough.Add('-SkipWsl') }
  if ($SkipDockerInstall)     { $passthrough.Add('-SkipDockerInstall') }
  if ($SkipGitHubCliInstall)  { $passthrough.Add('-SkipGitHubCliInstall') }
  if ($SkipPostgresInstall)   { $passthrough.Add('-SkipPostgresInstall') }
  if ($MaxAutoReboots -ne 2)  { $passthrough.Add('-MaxAutoReboots'); $passthrough.Add($MaxAutoReboots) }

  Write-Host "Not running elevated. Requesting admin rights now (a UAC prompt will appear) --" -ForegroundColor Yellow
  Write-Host "approve it to continue; this window will exit and a new elevated one will take over." -ForegroundColor Yellow
  Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList ($passthrough -join ' ')
  exit 0
}

# ---------------------------------------------------------------------------
# Logging: mirror all console output to a timestamped log file, same
# convention as ci-cd/staging_server_setup.sh's LOG_DIR/LOG_FILE handling.
# ---------------------------------------------------------------------------
$RunStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$LogFile = Join-Path $LogDir "machine1_env_setup_$RunStamp.log"
Start-Transcript -Path $LogFile -Append | Out-Null

function Write-Step  { param([string]$Text) Write-Host ""; Write-Host "== $Text ==" -ForegroundColor Cyan }
function Write-Ok    { param([string]$Text) Write-Host "  [OK] $Text" -ForegroundColor Green }
function Write-Warn2 { param([string]$Text) Write-Host "  [ACTION NEEDED] $Text" -ForegroundColor Yellow }
function Write-Skip  { param([string]$Text) Write-Host "  [SKIP] $Text" -ForegroundColor DarkGray }
function Test-CommandExists { param([string]$Name) return [bool](Get-Command $Name -ErrorAction SilentlyContinue) }

function Get-WindowsEditionType {
  # Win32_OperatingSystem.ProductType: 1 = Workstation (Windows 10/11 Desktop),
  # 2 = Domain Controller, 3 = Server. Used to gate Docker Desktop (Step 5),
  # which Docker's own system requirements list as Windows 10/11 only --
  # never Windows Server, regardless of WSL2 being enabled there.
  $ProductType = (Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction SilentlyContinue).ProductType
  if ($ProductType -eq 1) { return "Desktop" }
  return "Server"
}

function Test-WingetWorks {
  # A sideloaded App Installer package can be present on PATH but still
  # throw "No applicable app licenses found" when actually invoked (see
  # Step 0) -- Get-Command alone can't tell working from broken, so this
  # actually runs it and checks the exit code (via cmd /c, per the same
  # PowerShell 5.1 native-stderr-redirection caveat noted elsewhere here).
  if (-not (Test-CommandExists "winget")) { return $false }
  $null = cmd /c "winget --version" 2>&1
  return ($LASTEXITCODE -eq 0)
}

function Update-SessionPath {
  # An installer (winget, nvm-windows, ...) updates the registry's PATH but
  # this already-running process keeps its stale copy. Re-read Machine+User
  # PATH from the registry so newly installed commands are usable in the
  # same run, without needing a brand-new process or a reboot.
  $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
  $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
  $env:PATH = "$machinePath;$userPath"
}

# ---------------------------------------------------------------------------
# State: a small JSON file under machine1-setup-logs/ that survives across
# runs and reboots, so every step is idempotent -- re-running (including the
# automatic post-reboot resume) always picks up exactly where it left off.
# ---------------------------------------------------------------------------
function Get-State {
  if (Test-Path $StateFile) {
    try { return (Get-Content $StateFile -Raw | ConvertFrom-Json) } catch { }
  }
  return [PSCustomObject]@{
    version     = 1
    createdAt   = (Get-Date -Format o)
    updatedAt   = (Get-Date -Format o)
    rebootCount = 0
    steps       = [PSCustomObject]@{
      winget          = "not-started"
      node            = "not-started"
      python          = "not-started"
      wsl_feature     = "not-started"
      docker_desktop  = "not-started"
      github_cli      = "not-started"
      postgres_client = "not-started"
      redis_image     = "not-started"
      repo_scaffold   = "not-started"
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

$RunOnceKeyPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce"
$RunOnceValueName = "PhonemeMachineASetupResume"

function Invoke-ManagedReboot {
  param($State, [string]$Reason)

  $State.rebootCount = [int]$State.rebootCount + 1
  Save-State $State

  if ($State.rebootCount -gt $MaxAutoReboots) {
    Write-Warn2 "Hit the auto-reboot limit ($MaxAutoReboots) for this run -- not rebooting again automatically."
    Write-Warn2 "Reboot manually, then re-run this script once more; it will resume from the saved state ($StateFile)."
    Stop-Transcript | Out-Null
    exit 1
  }

  $resumeCmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $ScriptPath + '" -Resume'
  Set-ItemProperty -Path $RunOnceKeyPath -Name $RunOnceValueName -Value $resumeCmd -Force

  Write-Warn2 "Reboot required: $Reason"
  Write-Host "  This script has registered itself to auto-resume (via RunOnce) after you next log in." -ForegroundColor Yellow

  if ($NoAutoReboot) {
    Write-Warn2 "-NoAutoReboot set -- reboot manually when ready; this script will resume automatically at your next login."
    Stop-Transcript | Out-Null
    exit 0
  }

  Write-Host "  Rebooting automatically in 20 seconds. Save your work now -- press Ctrl+C to cancel." -ForegroundColor Yellow
  Start-Sleep -Seconds 20
  Stop-Transcript | Out-Null
  Restart-Computer -Force
}

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
    Write-Warn2 "winget not available -- cannot auto-install $FriendlyName. See MACHINE_A_SETUP_PROCESS.md for the manual winget bootstrap on Windows Server."
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

Write-Host "Run log: $LogFile"
Write-Host "State file: $StateFile"
Write-Host "Run started: $(Get-Date -Format o)"
Write-Host "Elevated session: $IsElevated"
if ($Resume) { Write-Host "This is an automatic post-reboot resume (triggered by RunOnce)." -ForegroundColor Cyan }
if ([int]$State.rebootCount -gt 0) { Write-Host "Prior auto-reboots this run: $($State.rebootCount)" }

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
    Write-Warn2 "winget not found (expected on Windows Server -- it isn't preinstalled there). Bootstrapping it..."
  }
  try {
    $ProgressPreference = 'SilentlyContinue'
    Write-Host "  Querying the latest winget-cli release from GitHub..."
    $Release = Invoke-RestMethod -Uri "https://api.github.com/repos/microsoft/winget-cli/releases/latest" -Headers @{ "User-Agent" = "PhonemeMachineASetup" } -TimeoutSec 30
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
    Write-Warn2 "Common causes on Windows Server: no outbound HTTPS path to github.com/api.github.com (corporate proxy/firewall -- this script does not read a proxy config), or this step not running elevated (DISM provisioning needs admin -- it should already have it by this point via the self-elevation above, unless -NoElevate was passed). See MACHINE_A_SETUP_PROCESS.md for the manual fallback."
  }
  if (Test-WingetWorks) {
    Set-StepStatus $State "winget" "done"
    Write-Ok "winget bootstrapped and confirmed working."
  } else {
    Write-Warn2 "winget still not functional after bootstrap -- see MACHINE_A_SETUP_PROCESS.md for the manual fallback. Steps below that depend on it will report blocked until this is resolved."
  }
}

# ---------------------------------------------------------------------------
Write-Step "Step 1: Node.js runtime version (Technical Stack Charter pin)"
if ($SkipNodePin) {
  Write-Skip "Node pin check skipped (-SkipNodePin)."
} else {
  $PinFile = Join-Path $RepoRoot ".nvmrc"
  $PinnedVersion = $null
  if (Test-Path $PinFile) { $PinnedVersion = (Get-Content $PinFile -Raw).Trim() }

  if (-not $PinnedVersion) {
    Write-Warn2 "No .nvmrc found at repo root -- cannot verify/pin the Node version."
  } else {
    Write-Host "  Pinned version (.nvmrc): $PinnedVersion"
    $ActiveVersion = if (Test-CommandExists "node") { (node -v).TrimStart("v") } else { $null }
    Write-Host "  Active 'node' on PATH: $ActiveVersion"
    if ($ActiveVersion -eq $PinnedVersion) {
      Set-StepStatus $State "node" "done"
      Write-Ok "Active Node already matches the pinned version."
    } else {
      Write-Warn2 "Active Node ($ActiveVersion) does not match the pin ($PinnedVersion) -- switching via nvm-windows."
      if (Install-ViaWinget -Id "CoreyButler.NVMforWindows" -FriendlyName "nvm-windows" -CheckCommand "nvm") {
        if ($DryRun) {
          Write-Skip "DryRun -- would run: nvm install $PinnedVersion; nvm use $PinnedVersion"
        } else {
          Write-Host "  Running: nvm install $PinnedVersion; nvm use $PinnedVersion"
          nvm install $PinnedVersion | Out-Null
          nvm use $PinnedVersion | Out-Null
          Update-SessionPath
          $ActiveVersion2 = if (Test-CommandExists "node") { (node -v).TrimStart("v") } else { $null }
          if ($ActiveVersion2 -eq $PinnedVersion) {
            Set-StepStatus $State "node" "done"
            Write-Ok "Node switched to the pinned $PinnedVersion via nvm-windows."
          } else {
            Write-Warn2 "nvm ran but 'node -v' now reports '$ActiveVersion2' -- open a new terminal and re-run this script to confirm."
            Set-StepStatus $State "node" "blocked"
          }
        }
      } else {
        Set-StepStatus $State "node" "blocked"
      }
    }
  }
}

# ---------------------------------------------------------------------------
Write-Step "Step 2: Python runtime version (Technical Stack Charter pin: 3.12.x)"
if (Test-CommandExists "python") {
  $PyVersion = (python --version).ToString().Replace("Python ", "").Trim()
  Write-Host "  Active 'python' on PATH: $PyVersion"
  if ($PyVersion -like "3.12.*") {
    Set-StepStatus $State "python" "done"
    Write-Ok "Python version matches the 3.12.x pin."
  } else {
    Write-Warn2 "Python $PyVersion does not match the pinned 3.12.x."
    Write-Warn2 "Not auto-remediated -- a different Python already first on PATH may be relied on elsewhere. Install Python 3.12 (winget install -e --id Python.Python.3.12) and put it first on PATH yourself."
    Set-StepStatus $State "python" "blocked"
  }
} else {
  Write-Warn2 "'python' not found on PATH -- installing Python 3.12."
  if (Install-ViaWinget -Id "Python.Python.3.12" -FriendlyName "Python 3.12" -CheckCommand "python") {
    Set-StepStatus $State "python" "done"
  } else {
    Set-StepStatus $State "python" "blocked"
  }
}

# ---------------------------------------------------------------------------
Write-Step "Step 3: Git identity and SSH key status (intentionally manual -- see script header)"
if (Test-CommandExists "git") {
  $GitName = git config --global user.name
  $GitEmail = git config --global user.email
  if ($GitName -and $GitEmail) {
    Write-Ok "Git identity configured: $GitName <$GitEmail>"
  } else {
    Write-Warn2 "Git identity not fully configured. Set it yourself with:"
    Write-Host "    git config --global user.name `"Your Name`"" -ForegroundColor Gray
    Write-Host "    git config --global user.email `"you@myphoneme.com`"" -ForegroundColor Gray
  }
} else {
  Write-Warn2 "git is not installed or not on PATH."
}

$SshDir = Join-Path $env:USERPROFILE ".ssh"
$DefaultKey = Join-Path $SshDir "id_ed25519"
if (Test-Path $DefaultKey) {
  Write-Ok "SSH key found at $DefaultKey"
  Write-Warn2 "This script does NOT register any key with GitHub. Per MACHINE1_READINESS.md, confirm with security that this machine is cleared post-incident before registering or trusting any key here -- rotate first if in doubt."
} else {
  Write-Warn2 "No default SSH key found at $DefaultKey. After security clearance, generate one with:"
  Write-Host "    ssh-keygen -t ed25519 -C `"you@myphoneme.com`"" -ForegroundColor Gray
  Write-Host "  then add the .pub key to GitHub -> Settings -> SSH and GPG keys (manual, owner action)."
}

# ---------------------------------------------------------------------------
Write-Step "Step 4: WSL2 Windows features"
if ($SkipWsl) {
  Write-Skip "WSL2 step skipped (-SkipWsl)."
} elseif ($State.steps.wsl_feature -eq "done") {
  Write-Ok "WSL2 already marked done in a prior run."
} else {
  $WslWorking = $false
  if (Test-CommandExists "wsl") {
    # Route through cmd /c rather than redirecting the native exe's stderr
    # directly in PowerShell 5.1 -- doing it here wraps each stderr line in
    # a NativeCommandError and can leak raw (garbled) output even though the
    # redirect target is $null. cmd handles the redirection itself instead.
    $null = cmd /c "wsl --status" 2>&1
    if ($LASTEXITCODE -eq 0) { $WslWorking = $true }
  }

  if ($WslWorking) {
    Set-StepStatus $State "wsl_feature" "done"
    Write-Ok "WSL2 is installed and responding."
    Remove-ItemProperty -Path $RunOnceKeyPath -Name $RunOnceValueName -ErrorAction SilentlyContinue
  } elseif ($DryRun) {
    Write-Skip "DryRun -- would enable the WSL2 Windows features and reboot if required."
  } else {
    Write-Warn2 "WSL2 not active -- enabling the required Windows features (Microsoft-Windows-Subsystem-Linux, VirtualMachinePlatform)."
    try {
      $f1 = Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -NoRestart -All
      $f2 = Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -NoRestart -All
      $NeedsRestart = $f1.RestartNeeded -or $f2.RestartNeeded
      if ($NeedsRestart) {
        Set-StepStatus $State "wsl_feature" "pending-reboot"
        Invoke-ManagedReboot -State $State -Reason "Enabling WSL2's Windows features requires a restart to take effect."
      } else {
        Set-StepStatus $State "wsl_feature" "done"
        Write-Ok "WSL2 features enabled (no restart was required)."
      }
    } catch {
      Write-Warn2 "Enabling WSL2 features failed: $($_.Exception.Message)"
      Write-Warn2 "This Windows edition/SKU may not support WSL2, or may need a Windows Update first -- see MACHINE_A_SETUP_PROCESS.md."
      Set-StepStatus $State "wsl_feature" "blocked"
    }
  }
}

# ---------------------------------------------------------------------------
Write-Step "Step 5: Docker Desktop"
$WindowsEdition = Get-WindowsEditionType
Write-Host "  Windows edition detected: $WindowsEdition"
if ($WindowsEdition -eq "Server") {
  Write-Host "  Note: Docker's own published system requirements list Windows 10/11 only, not Windows Server -- installing anyway, since this has been confirmed working here in practice. If you ever hit daemon/backend issues this step can't explain, that's the known gap to check first." -ForegroundColor DarkGray
}
if ($SkipDockerInstall) {
  Write-Skip "Docker Desktop install skipped (-SkipDockerInstall)."
} elseif ($State.steps.wsl_feature -ne "done") {
  Write-Skip "Waiting on WSL2 (previous step) before installing Docker Desktop."
} elseif (Install-ViaWinget -Id "Docker.DockerDesktop" -FriendlyName "Docker Desktop" -CheckCommand "docker") {
  Set-StepStatus $State "docker_desktop" "done"
  Write-Warn2 "One unavoidable manual step remains: launch Docker Desktop once from the Start Menu to accept its license and finish first-run setup -- winget cannot silently accept a GUI EULA."
} else {
  Set-StepStatus $State "docker_desktop" "blocked"
}

# ---------------------------------------------------------------------------
Write-Step "Step 6: GitHub CLI (gh)"
if ($SkipGitHubCliInstall) {
  Write-Skip "GitHub CLI install skipped (-SkipGitHubCliInstall)."
} elseif (Install-ViaWinget -Id "GitHub.cli" -FriendlyName "GitHub CLI" -CheckCommand "gh") {
  Set-StepStatus $State "github_cli" "done"
} else {
  Set-StepStatus $State "github_cli" "blocked"
}

# ---------------------------------------------------------------------------
Write-Step "Step 7: PostgreSQL 18 client"
if ($SkipPostgresInstall) {
  Write-Skip "PostgreSQL client install skipped (-SkipPostgresInstall)."
} else {
  $LegacyPgDir = "C:\Program Files\PostgreSQL\18"
  if (Test-Path $LegacyPgDir) {
    Write-Warn2 "A prior PostgreSQL 18 install directory still exists at $LegacyPgDir. Per MACHINE1_READINESS.md this was found ransomware-compromised on this machine -- not auto-installing over it."
    Write-Warn2 "Uninstall it via 'Add or remove programs' first, then re-run this script."
    Set-StepStatus $State "postgres_client" "blocked"
  } elseif (Install-ViaWinget -Id "PostgreSQL.PostgreSQL.18" -FriendlyName "PostgreSQL 18 client" -CheckCommand "psql") {
    Set-StepStatus $State "postgres_client" "done"
  } else {
    Set-StepStatus $State "postgres_client" "blocked"
  }
}
Write-Host "  Redis CLI: no official native Windows build -- see Step 8 (uses Docker instead)."

# ---------------------------------------------------------------------------
Write-Step "Step 8: Redis (via Docker -- no native Windows redis-cli)"
if (-not (Test-CommandExists "docker")) {
  Write-Skip "Docker not installed yet -- will retry on next run."
} else {
  $null = cmd /c "docker info" 2>&1
  if ($LASTEXITCODE -eq 0) {
    if ($DryRun) {
      Write-Skip "DryRun -- would run: docker pull redis:7"
    } else {
      Write-Host "  Pulling redis:7 for local dev use..."
      docker pull redis:7 | Out-Null
      Set-StepStatus $State "redis_image" "done"
      Write-Ok "redis:7 pulled. Use: docker run --rm -it redis:7 redis-cli -h host.docker.internal"
    }
  } else {
    Write-Skip "Docker installed but not responding yet -- launch Docker Desktop once (its first-run EULA, Step 5), then re-run this script."
  }
}

# ---------------------------------------------------------------------------
Write-Step "Step 9: Repo scaffold status (SOP 8.1 remaining steps -- Phase 2, not tooling)"
$Checks = [ordered]@{
  "package.json (any service)"        = (Get-ChildItem -Path $RepoRoot -Recurse -Filter "package.json" -ErrorAction SilentlyContinue -File | Where-Object { $_.FullName -notmatch "\\node_modules\\|\\\.tools\\" } | Select-Object -First 1)
  ".env.example"                      = (Test-Path (Join-Path $RepoRoot ".env.example"))
  "pre-commit config (.pre-commit-config.yaml)" = (Test-Path (Join-Path $RepoRoot ".pre-commit-config.yaml"))
  "requirements.txt / pyproject.toml (any service)" = (Get-ChildItem -Path $RepoRoot -Recurse -Include "requirements.txt","pyproject.toml" -ErrorAction SilentlyContinue -File | Where-Object { $_.FullName -notmatch "\\\.venv\\|\\venv\\|\\\.tools\\|\\node_modules\\" } | Select-Object -First 1)
}
$AnyMissing = $false
foreach ($Key in $Checks.Keys) {
  if ($Checks[$Key]) {
    Write-Ok "$Key -- found."
  } else {
    Write-Skip "$Key -- not present yet (Phase 2 scaffold, see MACHINE1_READINESS.md 'Next development gate')."
    $AnyMissing = $true
  }
}
if ($AnyMissing) {
  Set-StepStatus $State "repo_scaffold" "blocked"
  Write-Host ""
  Write-Host "  SOP 8.1's remaining local steps (install deps from lockfile, copy .env.example," -ForegroundColor DarkGray
  Write-Host "  enable pre-commit hooks, run the clean baseline build/unit suite) stay blocked" -ForegroundColor DarkGray
  Write-Host "  until the monorepo scaffold above is committed. This is expected at this stage." -ForegroundColor DarkGray
} else {
  Set-StepStatus $State "repo_scaffold" "done"
  Write-Ok "Scaffold present -- you can now run the dependency install / pre-commit / build steps."
}

# ---------------------------------------------------------------------------
Write-Step "Done -- current status"
$State = Get-State
foreach ($Key in $State.steps.PSObject.Properties.Name) {
  $Val = $State.steps.$Key
  switch ($Val) {
    "done"    { Write-Ok "$Key -- done" }
    { $_ -like "blocked*" } { Write-Warn2 "$Key -- $Val, see the step above" }
    default   { Write-Skip "$Key -- $Val" }
  }
}
Write-Host ""
Write-Host "Full log of this run saved to: $LogFile"
Write-Host "State file (re-run any time -- it resumes from here): $StateFile"

Stop-Transcript | Out-Null
