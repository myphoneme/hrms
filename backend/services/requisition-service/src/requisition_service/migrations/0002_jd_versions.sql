-- JD versions with an immutable history (HR-M1-FR-004; TDD §6.0 authoritative state model, §6 JDVersion).
-- Every edit is a new version with its author and timestamp; content is never changed after insert.
-- Only status (and superseded_by, when an Approved version is replaced) moves, along the allowed
-- transitions below. Versions are never deleted.

CREATE TYPE requisition.jd_variant_type   AS ENUM ('formal', 'candidate_friendly', 'condensed', 'manager_edited');
CREATE TYPE requisition.jd_generated_by   AS ENUM ('system', 'manager');
CREATE TYPE requisition.jd_version_status AS ENUM
  ('Draft', 'Revising', 'PendingApproval', 'Approved', 'Superseded', 'Rejected');

CREATE TABLE requisition.jd_version (
  id                  uuid PRIMARY KEY DEFAULT uuidv7(),
  requisition_id      uuid NOT NULL REFERENCES requisition.job_requisition (id),
  version_no          integer NOT NULL CHECK (version_no > 0),
  variant_type        requisition.jd_variant_type NOT NULL,
  content             text NOT NULL CHECK (btrim(content) <> ''),
  generated_by        requisition.jd_generated_by NOT NULL,
  status              requisition.jd_version_status NOT NULL DEFAULT 'Draft',
  -- The version this one revises (null for a first draft); keeps the edit history traceable.
  based_on_version_id uuid REFERENCES requisition.jd_version (id),
  -- Set only when an Approved version is replaced (Approved -> Superseded).
  superseded_by       uuid REFERENCES requisition.jd_version (id),
  created_by          uuid NOT NULL,
  created_at          timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT jd_version_requisition_version_no_key UNIQUE (requisition_id, version_no),
  CONSTRAINT jd_version_superseded_by_only_when_superseded
    CHECK ((status = 'Superseded') = (superseded_by IS NOT NULL))
);
CREATE INDEX jd_version_requisition_idx ON requisition.jd_version (requisition_id, version_no);

-- At most one Approved version per requisition at any moment (TDD §6).
CREATE UNIQUE INDEX jd_version_one_approved_per_requisition
  ON requisition.jd_version (requisition_id) WHERE status = 'Approved';

-- JobRequisition.active_version_id: the single currently-approved version.
ALTER TABLE requisition.job_requisition
  ADD CONSTRAINT job_requisition_active_version_fkey
  FOREIGN KEY (active_version_id) REFERENCES requisition.jd_version (id);

-- Content is immutable for every version; status moves only along TDD §6.0's transitions:
--   Draft           -> Revising | PendingApproval | Rejected
--   Revising        -> PendingApproval | Rejected
--   PendingApproval -> Revising | Approved | Rejected
--   Approved        -> Superseded   (only exception to Approved-row immutability, TDD §6)
--   Superseded, Rejected: final
CREATE FUNCTION requisition.jd_version_guard_update() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.requisition_id      IS DISTINCT FROM OLD.requisition_id
  OR NEW.version_no          IS DISTINCT FROM OLD.version_no
  OR NEW.variant_type        IS DISTINCT FROM OLD.variant_type
  OR NEW.content             IS DISTINCT FROM OLD.content
  OR NEW.generated_by        IS DISTINCT FROM OLD.generated_by
  OR NEW.based_on_version_id IS DISTINCT FROM OLD.based_on_version_id
  OR NEW.created_by          IS DISTINCT FROM OLD.created_by
  OR NEW.created_at          IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'JD version content is immutable; create a new version instead'
      USING ERRCODE = 'TM010', DETAIL = format('version %s (%s)', OLD.id, OLD.status);
  END IF;

  IF NEW.status IS DISTINCT FROM OLD.status AND NOT (
       (OLD.status = 'Draft'           AND NEW.status IN ('Revising', 'PendingApproval', 'Rejected'))
    OR (OLD.status = 'Revising'        AND NEW.status IN ('PendingApproval', 'Rejected'))
    OR (OLD.status = 'PendingApproval' AND NEW.status IN ('Revising', 'Approved', 'Rejected'))
    OR (OLD.status = 'Approved'        AND NEW.status = 'Superseded')
  ) THEN
    RAISE EXCEPTION 'JD version status cannot move from % to %', OLD.status, NEW.status
      USING ERRCODE = 'TM012';
  END IF;

  IF NEW.superseded_by IS DISTINCT FROM OLD.superseded_by
     AND NOT (OLD.status = 'Approved' AND NEW.status = 'Superseded') THEN
    RAISE EXCEPTION 'superseded_by is set only when an Approved version is superseded'
      USING ERRCODE = 'TM012';
  END IF;
  RETURN NEW;
END
$$;
CREATE TRIGGER jd_version_guard_update
  BEFORE UPDATE ON requisition.jd_version
  FOR EACH ROW EXECUTE FUNCTION requisition.jd_version_guard_update();

CREATE FUNCTION requisition.jd_version_guard_delete() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'JD versions are never deleted (audit trail)' USING ERRCODE = 'TM011';
END
$$;
CREATE TRIGGER jd_version_guard_delete
  BEFORE DELETE ON requisition.jd_version
  FOR EACH ROW EXECUTE FUNCTION requisition.jd_version_guard_delete();

-- A new version is always inserted as Draft or Revising; approval happens only through the
-- freeze transition (HR-M1-FR-006), never by inserting an Approved row.
CREATE FUNCTION requisition.jd_version_guard_insert() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.status NOT IN ('Draft', 'Revising') THEN
    RAISE EXCEPTION 'a new JD version must start as Draft or Revising, not %', NEW.status
      USING ERRCODE = 'TM012';
  END IF;
  IF NEW.based_on_version_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM requisition.jd_version b
     WHERE b.id = NEW.based_on_version_id AND b.requisition_id = NEW.requisition_id
  ) THEN
    RAISE EXCEPTION 'based_on_version_id must be a version of the same requisition' USING ERRCODE = 'TM013';
  END IF;
  RETURN NEW;
END
$$;
CREATE TRIGGER jd_version_guard_insert
  BEFORE INSERT ON requisition.jd_version
  FOR EACH ROW EXECUTE FUNCTION requisition.jd_version_guard_insert();

-- Row-Level Security: inherits the scope of its requisition (TDD §7.1 join-based policy).
ALTER TABLE requisition.jd_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE requisition.jd_version FORCE ROW LEVEL SECURITY;
CREATE POLICY parent_scope ON requisition.jd_version
  USING      (EXISTS (SELECT 1 FROM requisition.job_requisition r WHERE r.id = jd_version.requisition_id))
  WITH CHECK (EXISTS (SELECT 1 FROM requisition.job_requisition r WHERE r.id = jd_version.requisition_id));

-- Versions are append-only for the service role too: no DELETE (belt and braces with the trigger).
REVOKE DELETE ON requisition.jd_version FROM svc_requisition;
