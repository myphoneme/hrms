-- Teamora database bootstrap (entry point).
--
-- Creates the `teamora` database, its login roles, extensions and per-service schemas.
-- The same script runs in every environment (local, test, staging, production); only the
-- credentials differ, and they come from environment variables, never from this file
-- (Technical Stack Charter v1.1, "Database rules").
--
-- Run it as a PostgreSQL superuser, connected to the `postgres` maintenance database:
--   psql -X -v ON_ERROR_STOP=1 -d postgres -f backend/db/init/bootstrap.sql
-- or use the wrappers: backend/db/bootstrap.ps1 (Windows) / backend/db/bootstrap.sh (Linux, CI).
--
-- Safe to re-run: it only creates what is missing and re-applies roles, grants and passwords.
-- It never drops anything.

\set ON_ERROR_STOP on
\set QUIET on
-- Hide "already exists, skipping" notices on re-runs; warnings and errors still show.
SET client_min_messages = warning;

-- ---------------------------------------------------------------------------
-- 1. Read settings from the environment (requires psql 15+ for \getenv).
-- ---------------------------------------------------------------------------
\getenv app_env                   APP_ENV
\getenv migrator_password         POSTGRES_MIGRATOR_PASSWORD
\getenv svc_auth_password         POSTGRES_SVC_AUTH_PASSWORD
\getenv svc_requisition_password  POSTGRES_SVC_REQUISITION_PASSWORD
\getenv svc_publish_password      POSTGRES_SVC_PUBLISH_PASSWORD
\getenv svc_candidate_password    POSTGRES_SVC_CANDIDATE_PASSWORD
\getenv svc_dedupe_password       POSTGRES_SVC_DEDUPE_PASSWORD
\getenv svc_notification_password POSTGRES_SVC_NOTIFICATION_PASSWORD

\if :{?app_env}
\else
  \warn 'Missing environment variable: APP_ENV (local | test | staging | production)'
  \set bootstrap_failed true
\endif
\if :{?migrator_password}
\else
  \warn 'Missing environment variable: POSTGRES_MIGRATOR_PASSWORD'
  \set bootstrap_failed true
\endif
\if :{?svc_auth_password}
\else
  \warn 'Missing environment variable: POSTGRES_SVC_AUTH_PASSWORD'
  \set bootstrap_failed true
\endif
\if :{?svc_requisition_password}
\else
  \warn 'Missing environment variable: POSTGRES_SVC_REQUISITION_PASSWORD'
  \set bootstrap_failed true
\endif
\if :{?svc_publish_password}
\else
  \warn 'Missing environment variable: POSTGRES_SVC_PUBLISH_PASSWORD'
  \set bootstrap_failed true
\endif
\if :{?svc_candidate_password}
\else
  \warn 'Missing environment variable: POSTGRES_SVC_CANDIDATE_PASSWORD'
  \set bootstrap_failed true
\endif
\if :{?svc_dedupe_password}
\else
  \warn 'Missing environment variable: POSTGRES_SVC_DEDUPE_PASSWORD'
  \set bootstrap_failed true
\endif
\if :{?svc_notification_password}
\else
  \warn 'Missing environment variable: POSTGRES_SVC_NOTIFICATION_PASSWORD'
  \set bootstrap_failed true
\endif

\if :{?bootstrap_failed}
  DO $$ BEGIN RAISE EXCEPTION 'Bootstrap aborted: required environment variables are missing (see warnings above).'; END $$;
\endif

-- ---------------------------------------------------------------------------
-- 2. Validate the settings and the connecting user.
-- ---------------------------------------------------------------------------
SELECT
  :'app_env' IN ('local', 'test', 'staging', 'production') AS app_env_ok,
  -- pgvector is optional on developer machines (only Dedupe, Module 2, needs it) but
  -- mandatory on staging and production, which run the pgvector/pgvector:pg18 image.
  :'app_env' IN ('staging', 'production')                  AS require_vector,
  (SELECT rolsuper FROM pg_roles WHERE rolname = current_user) AS is_superuser,
  current_setting('server_version_num')::int >= 180000       AS pg18_or_newer,
  (SELECT bool_and(length(p) >= 12) FROM unnest(ARRAY[
     :'migrator_password', :'svc_auth_password', :'svc_requisition_password',
     :'svc_publish_password', :'svc_candidate_password', :'svc_dedupe_password',
     :'svc_notification_password']) AS p)                    AS passwords_ok
\gset

\if :app_env_ok
\else
  DO $$ BEGIN RAISE EXCEPTION 'Bootstrap aborted: APP_ENV must be one of local, test, staging, production.'; END $$;
\endif
\if :is_superuser
\else
  DO $$ BEGIN RAISE EXCEPTION 'Bootstrap aborted: connect as a PostgreSQL superuser (creates roles, the database and extensions).'; END $$;
\endif
\if :pg18_or_newer
\else
  DO $$ BEGIN RAISE EXCEPTION 'Bootstrap aborted: Teamora requires PostgreSQL 18 in every environment.'; END $$;
\endif
\if :passwords_ok
\else
  DO $$ BEGIN RAISE EXCEPTION 'Bootstrap aborted: every role password must be at least 12 characters.'; END $$;
\endif

\echo '== Teamora DB bootstrap'
\echo '   APP_ENV :' :app_env
\echo '   server  :' :HOST ':' :PORT
\echo '   as user :' :USER

-- ---------------------------------------------------------------------------
-- 3. Roles and database (connected to the maintenance database).
-- ---------------------------------------------------------------------------
\echo '-- 00: roles and database'
\ir 00_database_and_roles.sql

-- ---------------------------------------------------------------------------
-- 4. Extensions, schemas and grants (inside the teamora database).
--    \connect reuses the current host, port, user and password.
-- ---------------------------------------------------------------------------
\connect teamora
SET client_min_messages = warning;
\echo '-- 01: extensions'
\ir 01_extensions.sql
\echo '-- 02: schemas and grants'
\ir 02_schemas_and_grants.sql

\echo '== Done. Database "teamora" is ready for migrations (run them as teamora_migrator).'
