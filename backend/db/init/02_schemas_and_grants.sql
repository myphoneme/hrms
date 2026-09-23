-- 02: one schema per owning service, and each service role's access to it.
-- Runs inside the teamora database; included by bootstrap.sql.
--
-- Rules enforced here (Readiness doc §1.4, TDD §17.1):
--   * teamora_migrator owns every schema, so every table a migration creates is owned by it.
--   * Each svc_<service> role gets USAGE plus SELECT/INSERT/UPDATE/DELETE on ITS OWN schema only.
--     No CREATE, no TRUNCATE, no access to any other service's schema.
--   * Append-only tables (e.g. dedupe.duplicate_match, TDD §7.1) should REVOKE UPDATE/DELETE
--     in their own migration.
--   * Every multi-tenant table's migration must ENABLE and FORCE ROW LEVEL SECURITY.

-- Nothing lives in `public`; nobody may use it.
REVOKE ALL ON SCHEMA public FROM PUBLIC;

DO $$
DECLARE
  m record;
BEGIN
  FOR m IN
    SELECT * FROM (VALUES
      ('identity',     'svc_auth'),
      ('requisition',  'svc_requisition'),
      ('sourcing',     'svc_publish'),
      ('candidate',    'svc_candidate'),
      ('dedupe',       'svc_dedupe'),
      ('notification', 'svc_notification')
    ) AS t(schema_name, app_role)
  LOOP
    EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I AUTHORIZATION teamora_migrator', m.schema_name);
    EXECUTE format('ALTER SCHEMA %I OWNER TO teamora_migrator', m.schema_name);
    EXECUTE format('REVOKE ALL ON SCHEMA %I FROM PUBLIC', m.schema_name);
    EXECUTE format('GRANT USAGE ON SCHEMA %I TO %I', m.schema_name, m.app_role);

    -- Objects that already exist (makes re-runs repair missing grants).
    EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA %I TO %I', m.schema_name, m.app_role);
    EXECUTE format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %I TO %I', m.schema_name, m.app_role);
    EXECUTE format('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA %I TO %I', m.schema_name, m.app_role);

    -- Objects the migrator creates from now on.
    EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE teamora_migrator IN SCHEMA %I GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I', m.schema_name, m.app_role);
    EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE teamora_migrator IN SCHEMA %I GRANT USAGE, SELECT ON SEQUENCES TO %I', m.schema_name, m.app_role);
    EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE teamora_migrator IN SCHEMA %I GRANT EXECUTE ON FUNCTIONS TO %I', m.schema_name, m.app_role);

    -- Unqualified names resolve to the service's own schema, then extension types (citext, vector).
    EXECUTE format('ALTER ROLE %I IN DATABASE teamora SET search_path = %I, extensions', m.app_role, m.schema_name);
  END LOOP;
END
$$;

-- Migrations always schema-qualify their objects; the migrator only needs extension types on its path.
ALTER ROLE teamora_migrator IN DATABASE teamora SET search_path = extensions;
