import { ConflictException, Inject, Injectable, NotFoundException, UnprocessableEntityException } from '@nestjs/common';
import { AuthContext, DB_POOL, withTenant } from '@teamora/platform';
import { Pool, PoolClient } from 'pg';
import { notFound, tenantScopeOf } from '../common/tenant-scope';
import { AddCriterionInput, EditWeightsInput } from './scoring-matrix.validation';

export interface CriterionDto {
  criterion_id: string;
  criterion_name: string;
  category: string;
  weight_percent: number;
  source_field_ref: string | null;
}

/** TDD §8 GET .../scoring-matrix/draft response. */
export interface MatrixDto {
  matrix_id: string;
  jd_version_id: string;
  status: 'Draft' | 'Approved';
  matrix_revision: number;
  approved_at: string | null;
  criteria: CriterionDto[];
  current_total_percent: number;
}

/** JD version states whose matrix is still a working draft. */
const OPEN_VERSION_STATES = ['Draft', 'Revising', 'PendingApproval'];

@Injectable()
export class ScoringMatrixService {
  constructor(@Inject(DB_POOL) private readonly pool: Pool) {}

  /**
   * The draft matrix bound to one JD version (TDD §8). Created empty on first access while the version
   * is still open; in production the JD Generation worker fills it (HR-M1-FR-001/002).
   */
  getDraft(auth: AuthContext, requisitionId: string, versionId: string): Promise<MatrixDto> {
    return withTenant(this.pool, tenantScopeOf(auth), async (db) => {
      const version = await findVersion(db, requisitionId, versionId, false);
      const existing = await db.query<{ id: string }>('SELECT id FROM requisition.scoring_matrix WHERE jd_version_id = $1', [versionId]);
      if (existing.rows.length === 0) {
        if (!OPEN_VERSION_STATES.includes(version.status)) throw matrixNotFound();
        await db.query('INSERT INTO requisition.scoring_matrix (jd_version_id) VALUES ($1) ON CONFLICT (jd_version_id) DO NOTHING', [
          versionId,
        ]);
      }
      return loadMatrix(db, versionId);
    });
  }

  /**
   * Manager adjusts weights (TDD §8 PATCH). Only per-criterion bounds apply here; the sum-to-100 rule is
   * enforced at freeze, so a partial edit can be saved. `matrix_revision` must match (optimistic concurrency).
   */
  editWeights(auth: AuthContext, requisitionId: string, versionId: string, input: EditWeightsInput) {
    return this.withDraft(auth, requisitionId, versionId, input.matrixRevision, async (db, matrixId) => {
      const { rows } = await db.query<{ id: string }>('SELECT id FROM requisition.scoring_criterion WHERE matrix_id = $1', [matrixId]);
      const known = new Set(rows.map((r) => r.id));
      const unknown = input.criteria.filter((c) => !known.has(c.criterionId));
      if (unknown.length > 0) {
        throw new UnprocessableEntityException({
          reason: 'unknown_criterion',
          message: 'Some criterion_id values are not part of this matrix.',
          details: { criterion_ids: unknown.map((c) => c.criterionId) },
        });
      }
      for (const c of input.criteria) {
        await db.query('UPDATE requisition.scoring_criterion SET weight_percent = $2 WHERE id = $1', [c.criterionId, c.weightPercent]);
      }
      const matrix = await bumpRevision(db, matrixId, versionId);
      return { status: matrix.status, matrix_revision: matrix.matrix_revision, current_total_percent: matrix.current_total_percent };
    });
  }

  /** Adds a criterion by hand (the manual stand-in for generated criteria until HR-M1-FR-001). */
  addCriterion(auth: AuthContext, requisitionId: string, versionId: string, input: AddCriterionInput): Promise<MatrixDto> {
    return this.withDraft(auth, requisitionId, versionId, input.matrixRevision, async (db, matrixId) => {
      await db.query(
        'INSERT INTO requisition.scoring_criterion (matrix_id, category, criterion_name, weight_percent) VALUES ($1, $2, $3, $4)',
        [matrixId, input.category, input.criterionName, input.weightPercent],
      );
      return bumpRevision(db, matrixId, versionId);
    });
  }

  removeCriterion(auth: AuthContext, requisitionId: string, versionId: string, criterionId: string, revision: number): Promise<MatrixDto> {
    return this.withDraft(auth, requisitionId, versionId, revision, async (db, matrixId) => {
      const res = await db.query('DELETE FROM requisition.scoring_criterion WHERE id = $1 AND matrix_id = $2', [criterionId, matrixId]);
      if (res.rowCount === 0) {
        throw notFound('criterion');
      }
      return bumpRevision(db, matrixId, versionId);
    });
  }

  /** The Approved matrix of the requisition's current active version — what Module 3 scores against (TDD §8). */
  getApproved(auth: AuthContext, requisitionId: string): Promise<MatrixDto> {
    return withTenant(this.pool, tenantScopeOf(auth), async (db) => {
      const { rows } = await db.query<{ active_version_id: string | null }>(
        'SELECT active_version_id FROM requisition.job_requisition WHERE id = $1',
        [requisitionId],
      );
      if (rows.length === 0) throw notFound('requisition');
      if (rows[0].active_version_id === null) {
        throw new NotFoundException({ reason: 'no_approved_matrix', message: 'This requisition has not been frozen yet.' });
      }
      return loadMatrix(db, rows[0].active_version_id);
    });
  }

  /** Locks the draft matrix and checks it is still editable at the caller's revision before `fn` runs. */
  private withDraft<T>(
    auth: AuthContext,
    requisitionId: string,
    versionId: string,
    expectedRevision: number,
    fn: (db: PoolClient, matrixId: string) => Promise<T>,
  ): Promise<T> {
    return withTenant(this.pool, tenantScopeOf(auth), async (db) => {
      const version = await findVersion(db, requisitionId, versionId, true);
      const { rows } = await db.query<{ id: string; status: string; matrix_revision: number }>(
        'SELECT id, status, matrix_revision FROM requisition.scoring_matrix WHERE jd_version_id = $1 FOR UPDATE',
        [versionId],
      );
      if (rows.length === 0) throw matrixNotFound();
      const matrix = rows[0];
      if (matrix.status === 'Approved') {
        throw new ConflictException({ reason: 'matrix_approved', message: 'An Approved scoring matrix is immutable.' });
      }
      if (!OPEN_VERSION_STATES.includes(version.status)) {
        throw new ConflictException({
          reason: 'version_closed',
          message: `The JD version is ${version.status}; its matrix can no longer be edited.`,
        });
      }
      if (matrix.matrix_revision !== expectedRevision) {
        // Another edit landed first (e.g. a second browser tab): reject and return the current state (TDD §8).
        const current = await loadMatrix(db, versionId);
        throw new ConflictException({
          reason: 'revision_mismatch',
          message: 'The matrix changed since you last read it; re-apply your edit to the current state.',
          current_matrix_revision: current.matrix_revision,
          current_criteria: current.criteria,
        });
      }
      return fn(db, matrix.id);
    });
  }
}

async function findVersion(db: PoolClient, requisitionId: string, versionId: string, lock: boolean): Promise<{ status: string }> {
  const req = await db.query('SELECT 1 FROM requisition.job_requisition WHERE id = $1', [requisitionId]);
  if (req.rows.length === 0) throw notFound('requisition');
  const { rows } = await db.query<{ status: string }>(
    `SELECT status FROM requisition.jd_version WHERE id = $1 AND requisition_id = $2${lock ? ' FOR UPDATE' : ''}`,
    [versionId, requisitionId],
  );
  if (rows.length === 0) throw notFound('version');
  return rows[0];
}

async function bumpRevision(db: PoolClient, matrixId: string, versionId: string): Promise<MatrixDto> {
  await db.query('UPDATE requisition.scoring_matrix SET matrix_revision = matrix_revision + 1 WHERE id = $1', [matrixId]);
  return loadMatrix(db, versionId);
}

export async function loadMatrix(db: PoolClient, versionId: string): Promise<MatrixDto> {
  const { rows } = await db.query<{ id: string; status: 'Draft' | 'Approved'; matrix_revision: number; approved_at: Date | null }>(
    'SELECT id, status, matrix_revision, approved_at FROM requisition.scoring_matrix WHERE jd_version_id = $1',
    [versionId],
  );
  if (rows.length === 0) throw matrixNotFound();
  const matrix = rows[0];
  const criteria = await db.query<{ id: string; criterion_name: string; category: string; weight_percent: string; source_field_ref: string | null }>(
    `SELECT id, criterion_name, category, weight_percent, source_field_ref
       FROM requisition.scoring_criterion WHERE matrix_id = $1 ORDER BY category, created_at, id`,
    [matrix.id],
  );
  const list = criteria.rows.map((c) => ({
    criterion_id: c.id,
    criterion_name: c.criterion_name,
    category: c.category,
    weight_percent: Number(c.weight_percent),
    source_field_ref: c.source_field_ref,
  }));
  // Sum in hundredths to avoid floating-point drift (e.g. 33.33 + 33.33 + 33.34).
  const totalHundredths = list.reduce((sum, c) => sum + Math.round(c.weight_percent * 100), 0);
  return {
    matrix_id: matrix.id,
    jd_version_id: versionId,
    status: matrix.status,
    matrix_revision: matrix.matrix_revision,
    approved_at: matrix.approved_at ? matrix.approved_at.toISOString() : null,
    criteria: list,
    current_total_percent: totalHundredths / 100,
  };
}

function matrixNotFound(): NotFoundException {
  return new NotFoundException({ reason: 'matrix_not_found', message: 'This JD version has no scoring matrix.' });
}
