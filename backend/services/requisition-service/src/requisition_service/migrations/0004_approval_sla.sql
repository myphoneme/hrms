-- Approval SLA & escalation (HR-M1-FR-005; BRD §4.1 step 6; TDD §12.1 step 7, §14 "SLA escalation").
--
-- A JD version sent to the manager (PendingApproval) starts an SLA clock. If the manager hasn't
-- responded when the tenant's reminder threshold passes, a reminder is recorded for the manager; if
-- still unresolved at the escalation threshold, an escalation is recorded for the tenant's HR users.
-- Both are produced by a scheduled check (requisition_service.sla), never by a user request.
-- Delivery (email / portal) is the Notification Service's job; events wait here as 'pending'.
--
-- The manager has responded when the version leaves PendingApproval (freeze, revision, rejection) or
-- when the manager creates a newer version on the same requisition (TDD §6.0 review loop). Putting the
-- requisition OnHold or Closed also stops the clock. Triggers below keep the clocks right whatever
-- code path changes the data.

-- Per-tenant SLA settings (TDD §16.5: tenant-configurable). No row = the defaults (3 and 5 business days).
CREATE TABLE requisition.sla_policy (
  tenant_id                    uuid PRIMARY KEY REFERENCES identity.tenant (id),
  reminder_after_business_days integer NOT NULL CHECK (reminder_after_business_days BETWEEN 1 AND 20),
  escalate_after_business_days integer NOT NULL CHECK (escalate_after_business_days BETWEEN 2 AND 30),
  -- Business days are counted Monday-Friday in this IANA time zone (public holidays: not in Release 1).
  timezone                     text NOT NULL DEFAULT 'Asia/Kolkata' CHECK (btrim(timezone) <> ''),
  updated_by                   uuid NOT NULL,
  updated_at                   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT sla_policy_escalation_after_reminder CHECK (escalate_after_business_days > reminder_after_business_days)
);

ALTER TABLE requisition.sla_policy ENABLE ROW LEVEL SECURITY;
ALTER TABLE requisition.sla_policy FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON requisition.sla_policy
  USING      (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

-- SLA clocks: the scheduler's work list. One open clock per PendingApproval cycle of a version.
--
-- DELIBERATE EXCEPTION to "FORCE ROW LEVEL SECURITY on every multi-tenant table": the scheduled check
-- has to find due clocks across all tenants, and without a tenant scope RLS shows zero rows. This
-- table therefore holds ids and timestamps only (no JD text, names or other personal data); the check
-- re-reads the requisition, the version and the policy inside with_tenant(clock.tenant_id), under RLS,
-- before it records anything. No API reads this table directly.
CREATE TABLE requisition.approval_sla_clock (
  id               uuid PRIMARY KEY DEFAULT uuidv7(),
  tenant_id        uuid NOT NULL REFERENCES identity.tenant (id),
  requisition_id   uuid NOT NULL REFERENCES requisition.job_requisition (id),
  jd_version_id    uuid NOT NULL REFERENCES requisition.jd_version (id),
  pending_since    timestamptz NOT NULL DEFAULT now(),
  reminded_at      timestamptz,
  escalated_at     timestamptz,
  resolved_at      timestamptz,
  -- Why the clock stopped: the version's new status, 'revised' (a newer version was created) or the
  -- requisition's status (OnHold / Closed).
  resolution       text,
  CONSTRAINT approval_sla_clock_resolution_when_resolved CHECK ((resolved_at IS NULL) = (resolution IS NULL))
);
CREATE UNIQUE INDEX approval_sla_clock_one_open_per_version
  ON requisition.approval_sla_clock (jd_version_id) WHERE resolved_at IS NULL;
CREATE INDEX approval_sla_clock_open_idx
  ON requisition.approval_sla_clock (pending_since) WHERE resolved_at IS NULL;
CREATE INDEX approval_sla_clock_requisition_idx ON requisition.approval_sla_clock (requisition_id);
REVOKE DELETE ON requisition.approval_sla_clock FROM svc_requisition;

-- SLA events: the reminders and escalations, kept for audit and for the Notification Service to deliver.
CREATE TYPE requisition.sla_event_kind AS ENUM ('reminder', 'escalation');
CREATE TYPE requisition.sla_delivery_status AS ENUM ('pending', 'sent', 'failed');

CREATE TABLE requisition.approval_sla_event (
  id                uuid PRIMARY KEY DEFAULT uuidv7(),
  clock_id          uuid NOT NULL REFERENCES requisition.approval_sla_clock (id),
  tenant_id         uuid NOT NULL,
  requisition_id    uuid NOT NULL REFERENCES requisition.job_requisition (id),
  jd_version_id     uuid NOT NULL REFERENCES requisition.jd_version (id),
  kind              requisition.sla_event_kind NOT NULL,
  -- reminder -> the manager who owns the requisition; escalation -> every recruiter_hr user of the tenant.
  recipient_role    text NOT NULL CHECK (recipient_role IN ('manager', 'recruiter_hr')),
  recipient_user_id uuid,
  due_at            timestamptz NOT NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),
  delivery_status   requisition.sla_delivery_status NOT NULL DEFAULT 'pending',
  delivered_at      timestamptz,
  -- At most one reminder and one escalation per clock, even if two checks run at once.
  CONSTRAINT approval_sla_event_once_per_clock UNIQUE (clock_id, kind),
  CONSTRAINT approval_sla_event_recipient CHECK (
    (kind = 'reminder'   AND recipient_role = 'manager'      AND recipient_user_id IS NOT NULL) OR
    (kind = 'escalation' AND recipient_role = 'recruiter_hr' AND recipient_user_id IS NULL)
  )
);
CREATE INDEX approval_sla_event_tenant_idx ON requisition.approval_sla_event (tenant_id, created_at);
CREATE INDEX approval_sla_event_requisition_idx ON requisition.approval_sla_event (requisition_id);

ALTER TABLE requisition.approval_sla_event ENABLE ROW LEVEL SECURITY;
ALTER TABLE requisition.approval_sla_event FORCE ROW LEVEL SECURITY;
-- Inherits the requisition's scope (tenant, and client when the request is client-scoped).
CREATE POLICY parent_scope ON requisition.approval_sla_event
  USING      (EXISTS (SELECT 1 FROM requisition.job_requisition r WHERE r.id = approval_sla_event.requisition_id))
  WITH CHECK (EXISTS (SELECT 1 FROM requisition.job_requisition r WHERE r.id = approval_sla_event.requisition_id));
-- Events are an audit trail: never deleted.
REVOKE DELETE ON requisition.approval_sla_event FROM svc_requisition;

-- Clock maintenance on jd_version.
CREATE FUNCTION requisition.jd_version_sla_clock() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    -- A manager-created version is the manager's response to whatever was waiting on them.
    IF NEW.generated_by = 'manager' THEN
      UPDATE requisition.approval_sla_clock
         SET resolved_at = now(), resolution = 'revised'
       WHERE requisition_id = NEW.requisition_id AND resolved_at IS NULL;
    END IF;
    RETURN NEW;
  END IF;

  IF NEW.status = 'PendingApproval' AND OLD.status IS DISTINCT FROM 'PendingApproval' THEN
    INSERT INTO requisition.approval_sla_clock (tenant_id, requisition_id, jd_version_id)
    SELECT r.tenant_id, r.id, NEW.id FROM requisition.job_requisition r WHERE r.id = NEW.requisition_id;
  ELSIF OLD.status = 'PendingApproval' AND NEW.status IS DISTINCT FROM 'PendingApproval' THEN
    UPDATE requisition.approval_sla_clock
       SET resolved_at = now(), resolution = NEW.status::text
     WHERE jd_version_id = NEW.id AND resolved_at IS NULL;
  END IF;
  RETURN NEW;
END
$$;
CREATE TRIGGER jd_version_sla_clock
  AFTER INSERT OR UPDATE OF status ON requisition.jd_version
  FOR EACH ROW EXECUTE FUNCTION requisition.jd_version_sla_clock();

-- A requisition put OnHold or Closed stops its clocks.
CREATE FUNCTION requisition.job_requisition_sla_clock() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.status IN ('OnHold', 'Closed') AND OLD.status IS DISTINCT FROM NEW.status THEN
    UPDATE requisition.approval_sla_clock
       SET resolved_at = now(), resolution = NEW.status::text
     WHERE requisition_id = NEW.id AND resolved_at IS NULL;
  END IF;
  RETURN NEW;
END
$$;
CREATE TRIGGER job_requisition_sla_clock
  AFTER UPDATE OF status ON requisition.job_requisition
  FOR EACH ROW EXECUTE FUNCTION requisition.job_requisition_sla_clock();

-- No backfill: versions that were already PendingApproval before this migration get no clock. Nothing
-- has been deployed yet, so only local demo data is affected (re-seed it to get clocks). A backfill
-- isn't possible here anyway: migrations run without a tenant scope, and FORCE RLS hides every row.
