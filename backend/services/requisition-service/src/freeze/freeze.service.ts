import { ConflictException, Inject, Injectable, UnprocessableEntityException } from '@nestjs/common';
import { AuthContext, DB_POOL, isUuid, withTenant } from '@teamora/platform';
import { Pool, PoolClient } from 'pg';
import { notFound, tenantScopeOf } from '../common/tenant-scope';
import { loadMatrix } from '../scoring-matrix/scoring-matrix.service';

export interface FreezeInput {
  approvedVersionId: string;
  expectedActiveVersionId: string | null;
}

/** TDD §8 POST /freeze response. */
export interface FreezeResult {
  status: string;
  active_version_id: string;
  scoring_matrix_id: string;
  superseded_version_id: string | null;
}

/** `{ approved_version_id, expected_active_version_id }` — expected may be null but must be present. */
export function validateFreeze(body: unknown): FreezeInput {
  const input = (typeof body === 'object' && body !== null && !Array.isArray(body) ? body : null) as Record<string, unknown> | null;
  const problems: { field: string; problem: string }[] = [];
  if (!input) {
    problems.push({ field: '(body)', problem: 'must be a JSON object' });
  } else {
    if (!isUuid(input.approved_version_id)) problems.push({ field: 'approved_version_id', problem: 'must be a UUID' });
    if (!('expected_active_version_id' in input)) {
      problems.push({ field: 'expected_active_version_id', problem: 'is required (null if the requisition was never frozen)' });
    } else if (input.expected_active_version_id !== null && !isUuid(input.expected_active_version_id)) {
      problems.push({ field: 'expected_active_version_id', problem: 'must be a UUID or null' });
    }
  }
  if (problems.length > 0) {
    throw new UnprocessableEntityException({ reason: 'validation_failed', message: 'The request body is invalid.', details: problems });
  }
  return {
    approvedVersionId: input!.approved_version_id as string,
    expectedActiveVersionId: (input!.expected_active_version_id as string | null) ?? null,
  };
}

@Injectable()
export class FreezeService {
  constructor(@Inject(DB_POOL) private readonly pool: Pool) {}

  /**
   * Freeze (HR-M1-FR-006; TDD §8, §12.1 steps 8-9): approves one PendingApproval JD version and its draft
   * matrix in ONE transaction, supersedes the previously approved version (kept, never overwritten) and
   * repoints the requisition. The requisition row lock serialises concurrent freezes: exactly one wins.
   */
  freeze(auth: AuthContext, requisitionId: string, input: FreezeInput): Promise<FreezeResult> {
    return withTenant(this.pool, tenantScopeOf(auth), async (db) => {
      const { rows } = await db.query<{ status: string; active_version_id: string | null }>(
        'SELECT status, active_version_id FROM requisition.job_requisition WHERE id = $1 FOR UPDATE',
        [requisitionId],
      );
      if (rows.length === 0) throw notFound('requisition');
      const requisition = rows[0];

      // Exact repeat of a freeze that already succeeded: 200 no-op, same response (TDD §8 idempotency).
      if (requisition.active_version_id === input.approvedVersionId) {
        return resultFor(db, requisition.status, input.approvedVersionId);
      }
      if (requisition.status === 'OnHold' || requisition.status === 'Closed') {
        throw new ConflictException({
          reason: 'requisition_not_editable',
          message: `The requisition is ${requisition.status}; it can't be frozen.`,
        });
      }
      // Someone else's freeze landed first (TDD §8): exactly one concurrent caller's expectation matches.
      if (requisition.active_version_id !== input.expectedActiveVersionId) {
        throw new ConflictException({
          reason: 'stale_expected_version',
          message: 'The requisition was frozen by someone else since you last read it.',
          current_active_version_id: requisition.active_version_id,
        });
      }

      const version = await db.query<{ status: string }>(
        'SELECT status FROM requisition.jd_version WHERE id = $1 AND requisition_id = $2 FOR UPDATE',
        [input.approvedVersionId, requisitionId],
      );
      if (version.rows.length === 0 || version.rows[0].status !== 'PendingApproval') {
        throw new ConflictException({
          reason: 'version_not_approvable',
          message: 'Only a version awaiting approval (PendingApproval) can be frozen.',
          details: { current_status: version.rows[0]?.status ?? null },
        });
      }

      // Weights must total exactly 100 — rejected with the offending total, never normalised (BRD §5).
      const matrix = await db
        .query('SELECT 1 FROM requisition.scoring_matrix WHERE jd_version_id = $1 FOR UPDATE', [input.approvedVersionId])
        .then((r) => (r.rows.length > 0 ? loadMatrix(db, input.approvedVersionId) : null));
      if (matrix === null || matrix.current_total_percent !== 100) {
        throw new ConflictException({
          reason: 'matrix_total_invalid',
          message: 'The scoring matrix weights must total exactly 100% before freezing.',
          details: { current_total_percent: matrix?.current_total_percent ?? 0 },
        });
      }

      // Supersede first: at most one Approved version per requisition at any moment.
      if (requisition.active_version_id !== null) {
        await db.query("UPDATE requisition.jd_version SET status = 'Superseded', superseded_by = $2 WHERE id = $1", [
          requisition.active_version_id,
          input.approvedVersionId,
        ]);
      }
      await db.query("UPDATE requisition.jd_version SET status = 'Approved' WHERE id = $1", [input.approvedVersionId]);
      await db.query("UPDATE requisition.scoring_matrix SET status = 'Approved', approved_at = now() WHERE id = $1", [
        matrix.matrix_id,
      ]);
      await db.query(
        "UPDATE requisition.job_requisition SET active_version_id = $2, status = 'Frozen_Open', updated_at = now() WHERE id = $1",
        [requisitionId, input.approvedVersionId],
      );
      // requisition.frozen event for the Module 2 Publish Service (TDD §12.1 step 10) follows with the event backbone.
      return {
        status: 'Frozen_Open',
        active_version_id: input.approvedVersionId,
        scoring_matrix_id: matrix.matrix_id,
        superseded_version_id: requisition.active_version_id,
      };
    });
  }
}

async function resultFor(db: PoolClient, status: string, activeVersionId: string): Promise<FreezeResult> {
  const matrix = await db.query<{ id: string }>('SELECT id FROM requisition.scoring_matrix WHERE jd_version_id = $1', [activeVersionId]);
  const superseded = await db.query<{ id: string }>('SELECT id FROM requisition.jd_version WHERE superseded_by = $1', [activeVersionId]);
  return {
    status,
    active_version_id: activeVersionId,
    scoring_matrix_id: matrix.rows[0].id,
    superseded_version_id: superseded.rows[0]?.id ?? null,
  };
}
