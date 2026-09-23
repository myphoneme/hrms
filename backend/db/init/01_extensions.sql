-- 01: extensions, installed into their own `extensions` schema so `public` stays empty.
-- Runs inside the teamora database; included by bootstrap.sql (which sets :require_vector).

CREATE SCHEMA IF NOT EXISTS extensions;
REVOKE ALL ON SCHEMA extensions FROM PUBLIC;
GRANT USAGE ON SCHEMA extensions TO
  teamora_migrator, svc_auth, svc_requisition, svc_publish, svc_candidate, svc_dedupe, svc_notification;

-- pgcrypto: digests/HMAC helpers. citext: case-insensitive email columns (User.email, Candidate.email).
-- UUID primary keys need no extension: PostgreSQL 18 has built-in gen_random_uuid() and uuidv7().
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS citext   WITH SCHEMA extensions;

-- pgvector: similarity search for the Dedupe service (TDD §16, Module 2).
\if :require_vector
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;
\else
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector') THEN
    CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;
  ELSE
    RAISE WARNING 'pgvector is not installed on this server - skipped. Only the Dedupe service (Module 2) needs it; install pgvector and re-run this bootstrap before starting that work.';
  END IF;
END
$$;
\endif
