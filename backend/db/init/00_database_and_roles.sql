-- 00: login roles and the `teamora` database.
-- Runs connected to the maintenance database (`postgres`); included by bootstrap.sql,
-- which supplies the :'..._password' variables from the environment.
--
-- Roles (same names in every environment, only passwords differ):
--   teamora_migrator  owns the database and every service schema; the ONLY role that runs migrations.
--   svc_<service>     one per service that owns a schema; DML on its own schema only.
-- No role here may bypass Row-Level Security, and app roles never own tables
-- (PostgreSQL skips RLS for a table's owner) - see TDD §5.3.

-- Create any missing roles (attributes and passwords are applied below, every run).
SELECT format('CREATE ROLE %I', role_name)
FROM unnest(ARRAY[
  'teamora_migrator',
  'svc_auth',
  'svc_requisition',
  'svc_publish',
  'svc_candidate',
  'svc_dedupe',
  'svc_notification'
]) AS role_name
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name)
\gexec

ALTER ROLE teamora_migrator WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'migrator_password';
ALTER ROLE svc_auth         WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'svc_auth_password';
ALTER ROLE svc_requisition  WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'svc_requisition_password';
ALTER ROLE svc_publish      WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'svc_publish_password';
ALTER ROLE svc_candidate    WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'svc_candidate_password';
ALTER ROLE svc_dedupe       WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'svc_dedupe_password';
ALTER ROLE svc_notification WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'svc_notification_password';

-- The database. Same name in every environment (Charter v1.1, Database rules 3).
-- The builtin C.UTF-8 locale provider (PostgreSQL 17+) gives identical sorting and
-- case rules on Windows developer machines and Linux servers, independent of OS locales.
SELECT 'CREATE DATABASE teamora WITH OWNER teamora_migrator TEMPLATE template0 ENCODING ''UTF8'''
       ' LOCALE_PROVIDER builtin BUILTIN_LOCALE ''C.UTF-8'' LC_COLLATE ''C'' LC_CTYPE ''C'''
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'teamora')
\gexec

ALTER DATABASE teamora OWNER TO teamora_migrator;

-- Only Teamora roles may connect.
REVOKE ALL ON DATABASE teamora FROM PUBLIC;
GRANT CONNECT ON DATABASE teamora TO
  teamora_migrator, svc_auth, svc_requisition, svc_publish, svc_candidate, svc_dedupe, svc_notification;
