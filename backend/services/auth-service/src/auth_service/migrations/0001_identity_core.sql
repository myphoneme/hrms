-- Identity core: tenants, agency clients and users (TDD §3.1, §3.2, §5.1).
-- Owned by auth-service. Runs as teamora_migrator; svc_auth gets DML through the default
-- privileges set by backend/db/init. Every table is tenant-isolated by Row-Level Security.

CREATE TYPE identity.org_type      AS ENUM ('direct_employer', 'staffing_agency');
CREATE TYPE identity.client_status AS ENUM ('active', 'offboarded');
CREATE TYPE identity.auth_method   AS ENUM ('sso_google', 'sso_microsoft', 'local_password');
CREATE TYPE identity.user_role     AS ENUM ('platform_admin', 'tenant_admin', 'manager', 'recruiter_hr');

-- Tenant: a direct employer, or a staffing agency acting for end-client companies (TDD §5.1).
CREATE TABLE identity.tenant (
  id         uuid PRIMARY KEY DEFAULT uuidv7(),
  org_type   identity.org_type NOT NULL,
  name       text NOT NULL CHECK (btrim(name) <> ''),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Client: an end-client company managed by a staffing-agency tenant.
CREATE TABLE identity.client (
  id               uuid PRIMARY KEY DEFAULT uuidv7(),
  agency_tenant_id uuid NOT NULL REFERENCES identity.tenant (id),
  name             text NOT NULL CHECK (btrim(name) <> ''),
  status           identity.client_status NOT NULL DEFAULT 'active',
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now(),
  -- Lets other schemas reference (client_id, tenant_id) together, so a record can never point at
  -- another tenant's client (used by requisition.job_requisition).
  CONSTRAINT client_id_tenant_key UNIQUE (id, agency_tenant_id)
);
CREATE INDEX client_agency_tenant_idx ON identity.client (agency_tenant_id);

-- User (TDD §3.1 field table). Named app_user because "user" is reserved in SQL.
CREATE TABLE identity.app_user (
  id            uuid PRIMARY KEY DEFAULT uuidv7(),
  tenant_id     uuid REFERENCES identity.tenant (id),
  email         extensions.citext NOT NULL,
  auth_method   identity.auth_method NOT NULL,
  password_hash text,
  mfa_enabled   boolean NOT NULL DEFAULT false,
  role          identity.user_role NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  -- Null tenant only for a Phoneme Platform Admin, who is not scoped to any tenant (TDD §3.2).
  CONSTRAINT app_user_platform_admin_scope CHECK ((role = 'platform_admin') = (tenant_id IS NULL)),
  -- TOTP MFA is mandatory for the Platform Admin regardless of tenant policy (TDD §3.1).
  CONSTRAINT app_user_platform_admin_mfa CHECK (role <> 'platform_admin' OR mfa_enabled),
  -- Argon2id hash only for local-password users; always null on an SSO path (TDD §3.1).
  CONSTRAINT app_user_password_local_only CHECK (auth_method = 'local_password' OR password_hash IS NULL),
  -- Email is unique within a tenant (platform admins share the null "tenant").
  CONSTRAINT app_user_tenant_email_key UNIQUE NULLS NOT DISTINCT (tenant_id, email)
);

-- A client can only belong to a staffing agency (TDD §5.1).
-- If the tenant row isn't visible (another tenant, hidden by RLS) or doesn't exist, this trigger
-- leaves the rejection to the RLS WITH CHECK / foreign key, so the reported error is the real one.
CREATE FUNCTION identity.client_requires_agency() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  tenant_org_type identity.org_type;
BEGIN
  SELECT org_type INTO tenant_org_type FROM identity.tenant WHERE id = NEW.agency_tenant_id;
  IF FOUND AND tenant_org_type <> 'staffing_agency' THEN
    RAISE EXCEPTION 'a client must belong to a staffing_agency tenant'
      USING ERRCODE = 'TM003', DETAIL = format('tenant %s', NEW.agency_tenant_id);
  END IF;
  RETURN NEW;
END
$$;
CREATE TRIGGER client_requires_agency
  BEFORE INSERT OR UPDATE OF agency_tenant_id ON identity.client
  FOR EACH ROW EXECUTE FUNCTION identity.client_requires_agency();

-- org_type is fixed at creation: requisitions and clients depend on it (TDD §5.2).
CREATE FUNCTION identity.tenant_org_type_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.org_type IS DISTINCT FROM OLD.org_type THEN
    RAISE EXCEPTION 'tenant org_type cannot be changed' USING ERRCODE = 'TM004';
  END IF;
  RETURN NEW;
END
$$;
CREATE TRIGGER tenant_org_type_immutable
  BEFORE UPDATE OF org_type ON identity.tenant
  FOR EACH ROW EXECUTE FUNCTION identity.tenant_org_type_immutable();

-- Row-Level Security (TDD §5.3). FORCE applies it to the table owner too. A connection without
-- app.tenant_id set (see withTenant in @teamora/platform) sees zero rows, never all rows.
ALTER TABLE identity.tenant   ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity.tenant   FORCE ROW LEVEL SECURITY;
ALTER TABLE identity.client   ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity.client   FORCE ROW LEVEL SECURITY;
ALTER TABLE identity.app_user ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity.app_user FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON identity.tenant
  USING      (id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  WITH CHECK (id = nullif(current_setting('app.tenant_id', true), '')::uuid);

CREATE POLICY tenant_isolation ON identity.client
  USING      (agency_tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  WITH CHECK (agency_tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

CREATE POLICY tenant_isolation ON identity.app_user
  USING      (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);
