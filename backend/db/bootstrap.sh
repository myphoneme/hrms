#!/usr/bin/env sh
# Creates or updates the Teamora database (roles, database, extensions, schemas) on a PostgreSQL 18 server.
#
# Linux / CI / Coolify wrapper around backend/db/init/bootstrap.sql. Loads backend/.env if present
# (values already set in the environment win), then runs the bootstrap as a superuser with psql.
# Safe to re-run; it never drops anything.
#
# Connection: standard libpq variables PGHOST (default localhost), PGPORT (default 5432),
# PGUSER (default postgres), PGPASSWORD (or psql prompts).
#
# Usage: backend/db/bootstrap.sh [path/to/.env]
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENV_FILE=${1:-"$SCRIPT_DIR/../.env"}

if [ -f "$ENV_FILE" ]; then
  echo "Loading $ENV_FILE"
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|'#'*) continue ;; esac
    name=${line%%=*}
    value=${line#*=}
    name=$(printf '%s' "$name" | tr -d '[:space:]')
    value=$(printf '%s' "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'$/\1/")
    # Keep values already exported in the environment.
    if [ -z "$(printenv "$name" 2>/dev/null || true)" ]; then
      export "$name=$value"
    fi
  done < "$ENV_FILE"
else
  echo "No .env file at $ENV_FILE - using variables already set in the environment."
fi

export PGHOST="${PGHOST:-localhost}"
export PGPORT="${PGPORT:-5432}"
export PGUSER="${PGUSER:-postgres}"

exec psql -X -v ON_ERROR_STOP=1 -d postgres -f "$SCRIPT_DIR/init/bootstrap.sql"
