-- Draft-then-freeze weighted scoring matrix (HR-M1-FR-006; TDD §6 ScoringMatrix/ScoringCriterion, §8).
-- One matrix per JD version (not per requisition), editable while Draft, approved atomically with its
-- JD version at freeze, and immutable afterwards. Screening categories only: soft-skill / behavioral
-- signals are excluded from numeric scoring by business decision (BRD §4.1), so there is no such category.

CREATE TYPE requisition.matrix_status      AS ENUM ('Draft', 'Approved');
CREATE TYPE requisition.criterion_category AS ENUM
  ('core_skills', 'experience_seniority', 'domain_competency', 'education_fit');

CREATE TABLE requisition.scoring_matrix (
  id              uuid PRIMARY KEY DEFAULT uuidv7(),
  jd_version_id   uuid NOT NULL REFERENCES requisition.jd_version (id),
  status          requisition.matrix_status NOT NULL DEFAULT 'Draft',
  -- Optimistic-concurrency counter for draft edits (TDD §8 PATCH .../scoring-matrix/draft).
  matrix_revision integer NOT NULL DEFAULT 1 CHECK (matrix_revision > 0),
  approved_at     timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT scoring_matrix_jd_version_key UNIQUE (jd_version_id),
  CONSTRAINT scoring_matrix_approved_at_iff_approved CHECK ((status = 'Approved') = (approved_at IS NOT NULL))
);

CREATE TABLE requisition.scoring_criterion (
  id               uuid PRIMARY KEY DEFAULT uuidv7(),
  matrix_id        uuid NOT NULL REFERENCES requisition.scoring_matrix (id),
  category         requisition.criterion_category NOT NULL,
  criterion_name   text NOT NULL CHECK (btrim(criterion_name) <> ''),
  weight_percent   numeric(5, 2) NOT NULL CHECK (weight_percent >= 0 AND weight_percent <= 100),
  -- Traceability to the JDField it was generated from (HR-M1-FR-001); null for manager-added criteria.
  source_field_ref uuid,
  created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX scoring_criterion_matrix_idx ON requisition.scoring_criterion (matrix_id);

-- Matrix: Draft -> Approved only when its weights total exactly 100 (TM021) and its JD version is
-- already Approved in the same transaction (TM022); an Approved matrix never changes (TM020).
CREATE FUNCTION requisition.scoring_matrix_guard_update() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  total numeric;
BEGIN
  IF OLD.status = 'Approved' THEN
    RAISE EXCEPTION 'an Approved scoring matrix is immutable' USING ERRCODE = 'TM020';
  END IF;
  IF NEW.jd_version_id IS DISTINCT FROM OLD.jd_version_id OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'a scoring matrix stays bound to its JD version' USING ERRCODE = 'TM020';
  END IF;
  IF NEW.status = 'Approved' THEN
    SELECT coalesce(sum(weight_percent), 0) INTO total FROM requisition.scoring_criterion WHERE matrix_id = NEW.id;
    IF total <> 100 THEN
      RAISE EXCEPTION 'scoring matrix weights must total exactly 100 to approve (total %)', total
        USING ERRCODE = 'TM021';
    END IF;
    IF (SELECT status FROM requisition.jd_version WHERE id = NEW.jd_version_id) IS DISTINCT FROM 'Approved' THEN
      RAISE EXCEPTION 'a scoring matrix is approved only together with its JD version' USING ERRCODE = 'TM022';
    END IF;
  END IF;
  RETURN NEW;
END
$$;
CREATE TRIGGER scoring_matrix_guard_update
  BEFORE UPDATE ON requisition.scoring_matrix
  FOR EACH ROW EXECUTE FUNCTION requisition.scoring_matrix_guard_update();

-- A new matrix always starts as Draft.
CREATE FUNCTION requisition.scoring_matrix_guard_insert() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.status <> 'Draft' THEN
    RAISE EXCEPTION 'a new scoring matrix must start as Draft' USING ERRCODE = 'TM020';
  END IF;
  RETURN NEW;
END
$$;
CREATE TRIGGER scoring_matrix_guard_insert
  BEFORE INSERT ON requisition.scoring_matrix
  FOR EACH ROW EXECUTE FUNCTION requisition.scoring_matrix_guard_insert();

-- Criteria can only be added, changed or removed while their matrix is Draft (TM020).
CREATE FUNCTION requisition.scoring_criterion_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  matrix uuid := CASE WHEN TG_OP = 'DELETE' THEN OLD.matrix_id ELSE NEW.matrix_id END;
BEGIN
  IF (SELECT status FROM requisition.scoring_matrix WHERE id = matrix) = 'Approved'
     OR (TG_OP = 'UPDATE' AND NEW.matrix_id IS DISTINCT FROM OLD.matrix_id) THEN
    RAISE EXCEPTION 'criteria of an Approved scoring matrix are immutable' USING ERRCODE = 'TM020';
  END IF;
  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END
$$;
CREATE TRIGGER scoring_criterion_guard
  BEFORE INSERT OR UPDATE OR DELETE ON requisition.scoring_criterion
  FOR EACH ROW EXECUTE FUNCTION requisition.scoring_criterion_guard();

-- Row-Level Security: both tables inherit the requisition's scope through their parents.
ALTER TABLE requisition.scoring_matrix    ENABLE ROW LEVEL SECURITY;
ALTER TABLE requisition.scoring_matrix    FORCE ROW LEVEL SECURITY;
ALTER TABLE requisition.scoring_criterion ENABLE ROW LEVEL SECURITY;
ALTER TABLE requisition.scoring_criterion FORCE ROW LEVEL SECURITY;

CREATE POLICY parent_scope ON requisition.scoring_matrix
  USING      (EXISTS (SELECT 1 FROM requisition.jd_version v WHERE v.id = scoring_matrix.jd_version_id))
  WITH CHECK (EXISTS (SELECT 1 FROM requisition.jd_version v WHERE v.id = scoring_matrix.jd_version_id));

CREATE POLICY parent_scope ON requisition.scoring_criterion
  USING      (EXISTS (SELECT 1 FROM requisition.scoring_matrix m WHERE m.id = scoring_criterion.matrix_id))
  WITH CHECK (EXISTS (SELECT 1 FROM requisition.scoring_matrix m WHERE m.id = scoring_criterion.matrix_id));

-- Matrices are kept for every version's history (assessments refer to them): never deleted.
REVOKE DELETE ON requisition.scoring_matrix FROM svc_requisition;
