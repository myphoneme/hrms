<#
.SYNOPSIS
  Creates or updates the Teamora database (roles, database, extensions, schemas) on a PostgreSQL 18 server.

.DESCRIPTION
  Windows wrapper around backend/db/init/bootstrap.sql. It loads variables from backend/.env
  (values already set in the environment win), then runs the bootstrap as a superuser with psql.
  Safe to re-run; it never drops anything.

  Connection settings use the standard libpq variables: PGHOST (default localhost), PGPORT (default 5432),
  PGUSER (default postgres). psql prompts for the superuser password unless PGPASSWORD is set.

.PARAMETER EnvFile
  Path to the .env file to load. Default: backend/.env next to this script's folder.

.EXAMPLE
  cd backend
  .\db\bootstrap.ps1
#>
param(
  [string]$EnvFile = (Join-Path (Split-Path $PSScriptRoot -Parent) ".env")
)

$ErrorActionPreference = "Stop"

if (Test-Path $EnvFile) {
  Write-Host "Loading $EnvFile"
  foreach ($line in Get-Content $EnvFile) {
    if ($line -match '^\s*(#|$)') { continue }
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$') {
      $name = $Matches[1]
      $value = $Matches[2].Trim('"').Trim("'")
      if (-not [Environment]::GetEnvironmentVariable($name, "Process")) {
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
      }
    }
  }
} else {
  Write-Host "No .env file at $EnvFile - using variables already set in this shell."
}

$psql = Get-Command psql -ErrorAction SilentlyContinue
if (-not $psql) {
  $fallback = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
  if (Test-Path $fallback) { $psql = Get-Command $fallback } else { throw "psql not found. Install the PostgreSQL 18 client or add its bin folder to PATH." }
}

if (-not $env:PGHOST) { $env:PGHOST = "localhost" }
if (-not $env:PGPORT) { $env:PGPORT = "5432" }
if (-not $env:PGUSER) { $env:PGUSER = "postgres" }

$script = Join-Path $PSScriptRoot "init\bootstrap.sql"
& $psql.Source -X -v ON_ERROR_STOP=1 -d postgres -f $script
exit $LASTEXITCODE
