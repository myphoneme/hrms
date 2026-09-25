-- Requisition intake: JobRequisition + JDBrief (TDD §6, §8 POST /requisitions/intake; HR-M1-FR-007).
-- Owned by requisition-service, which owns every Module 1 table (TDD review decision B3, PR #7).
-- Runs as teamora_migrator after the identity migrations (it references identity.tenant/client).

CREATE TYPE requisition.requisition_status AS ENUM
  ('Draft', 'PendingApproval', 'Revising', 'Frozen_Open', 'OnHold', 'Closed');
CREATE TYPE requisition.brief_source AS ENUM ('email', 'portal');

CREATE TABLE requisition.job_requisition (
  id                uuid PRIMARY KEY DEFAULT uuidv7(),
  tenant_id         uuid NOT NULL,
  -- Mandatory for staffing_agency tenants, explicitly null for direct_employer tenants (TDD §5.2).
  client_id         uuid,
  department_id     uuid,
  status            requisition.requisition_status NOT NULL DEFAULT 'Draft',
  -- Points at the approved JDVersion once one exists (FK added with the jd_version table).
  active_version_id uuid,
  created_by        uuid NOT NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT job_requisition_tenant_fkey FOREIGN KEY (tenant_id) REFERENCES identity.tenant (id),
  -- The client must belong to the same tenant: referencing (client_id, tenant_id) together makes a
  -- requisition pointing at another tenant's client impossible. Not checked when client_id is null.
  CONSTRAINT job_requisition_client_fkey FOREIGN KEY (client_id, tenant_id)
    REFERENCES identity.client (id, agency_tenant_id)
);
CREATE INDEX job_requisition_tenant_client_idx ON requisition.job_requisition (tenant_id, client_id);

CREATE TABLE requisition.jd_brief (
  id             uuid PRIMARY KEY DEFAULT uuidv7(),
  requisition_id uuid NOT NULL REFERENCES requisition.job_requisition (id) ON DELETE CASCADE,
  raw_text       text NOT NULL CHECK (btrim(raw_text) <> ''),
  source         requisition.brief_source NOT NULL,
  received_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX jd_brief_requisition_idx ON requisition.jd_brief (requisition_id);

-- HR-M1-FR-007 enforced in the database, whatever the caller (API, script, batch job):
--   staffing_agency tenant -> client_id required  (TM001)
--   direct_employer tenant -> client_id must be null (TM002)
-- SECURITY DEFINER so it can read identity.tenant, which svc_requisition has no access to. It still
-- sees only the caller's own tenant (Row-Level Security is forced for the owner too); if the tenant
-- isn't visible, it leaves the rejection to the RLS WITH CHECK / foreign key.
CREATE FUNCTION requisition.check_client_matches_org_type() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
DECLARE
  tenant_org_type identity.org_type;
BEGIN
  SELECT t.org_type INTO tenant_org_type FROM identity.tenant t WHERE t.id = NEW.tenant_id;
  IF NOT FOUND THEN
    RETURN NEW;
  END IF;
  IF tenant_org_type = 'staffing_agency' AND NEW.client_id IS NULL THEN
    RAISE EXCEPTION 'a staffing-agency requisition must specify client_id' USING ERRCODE = 'TM001';
  END IF;
  IF tenant_org_type = 'direct_employer' AND NEW.client_id IS NOT NULL THEN
    RAISE EXCEPTION 'a direct-employer requisition must not specify client_id' USING ERRCODE = 'TM002';
  END IF;
  RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION requisition.check_client_matches_org_type() FROM PUBLIC;

CREATE TRIGGER check_client_matches_org_type
  BEFORE INSERT OR UPDATE OF tenant_id, client_id ON requisition.job_requisition
  FOR EACH ROW EXECUTE FUNCTION requisition.check_client_matches_org_type();

-- Row-Level Security (TDD §5.3): scoped by tenant, and by client when the request is client-scoped.
ALTER TABLE requisition.job_requisition ENABLE ROW LEVEL SECURITY;
ALTER TABLE requisition.job_requisition FORCE ROW LEVEL SECURITY;
ALTER TABLE requisition.jd_brief        ENABLE ROW LEVEL SECURITY;
ALTER TABLE requisition.jd_brief        FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_client_isolation ON requisition.job_requisition
  USING (
    tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid
    AND (nullif(current_setting('app.client_id', true), '') IS NULL
         OR client_id = nullif(current_setting('app.client_id', true), '')::uuid)
  )
  WITH CHECK (
    tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid
    AND (nullif(current_setting('app.client_id', true), '') IS NULL
         OR client_id = nullif(current_setting('app.client_id', true), '')::uuid)
  );

-- JDBrief inherits its scope from the parent requisition (TDD §7.1: join-based policy).
CREATE POLICY parent_scope ON requisition.jd_brief
  USING      (EXISTS (SELECT 1 FROM requisition.job_requisition r WHERE r.id = jd_brief.requisition_id))
  WITH CHECK (EXISTS (SELECT 1 FROM requisition.job_requisition r WHERE r.id = jd_brief.requisition_id));
