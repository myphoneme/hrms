import { ConflictException, Inject, Injectable, UnprocessableEntityException } from '@nestjs/common';
import { AuthContext, DB_POOL, withTenant } from '@teamora/platform';
import { Pool, PoolClient } from 'pg';
import { notFound, tenantScopeOf } from '../common/tenant-scope';
import { CreateVersionInput } from './jd-versions.validation';

export type VersionStatus = 'Draft' | 'Revising' | 'PendingApproval' | 'Approved' | 'Superseded' | 'Rejected';

/** API representation of a JDVersion (TDD §6, §8 GET /jd-versions). */
export interface JdVersionDto {
  id: string;
  requisition_id: string;
  version_no: number;
  variant_type: string;
  generated_by: string;
  status: VersionStatus;
  based_on_version_id: string | null;
  superseded_by: string | null;
  created_by: string;
  created_at: string;
  content: string;
}

const VERSION_COLUMNS = `id, requisition_id, version_no, variant_type, generated_by, status,
  based_on_version_id, superseded_by, created_by, created_at, content`;

/** Requisition states in which JD work can no longer happen. */
const CLOSED_STATES = ['OnHold', 'Closed'];

@Injectable()
export class JdVersionsService {
  constructor(@Inject(DB_POOL) private readonly pool: Pool) {}

  /** The full, immutable history of a requisition's JD versions, in version order. */
  async list(auth: AuthContext, requisitionId: string): Promise<JdVersionDto[]> {
    return withTenant(this.pool, tenantScopeOf(auth), async (db) => {
      await findRequisition(db, requisitionId, false);
      const { rows } = await db.query<JdVersionDto>(
        `SELECT ${VERSION_COLUMNS} FROM requisition.jd_version WHERE requisition_id = $1 ORDER BY version_no`,
        [requisitionId],
      );
      return rows.map(toDto);
    });
  }

  /**
   * Stores an edit as a new version (HR-M1-FR-004): a first draft is `Draft`; a revision of an existing
   * version (`based_on_version_id`) is `Revising`. Existing versions are never modified.
   */
  async create(auth: AuthContext, requisitionId: string, input: CreateVersionInput): Promise<JdVersionDto> {
    try {
      return await withTenant(this.pool, tenantScopeOf(auth), async (db) => {
        const requisition = await findRequisition(db, requisitionId, true);
        assertOpen(requisition.status);
        const status: VersionStatus = input.basedOnVersionId ? 'Revising' : 'Draft';
        const { rows } = await db.query<JdVersionDto>(
          `INSERT INTO requisition.jd_version
             (requisition_id, version_no, variant_type, content, generated_by, status, based_on_version_id, created_by)
           SELECT $1, coalesce(max(version_no), 0) + 1, $2, $3, 'manager', $4, $5, $6
             FROM requisition.jd_version WHERE requisition_id = $1
           RETURNING ${VERSION_COLUMNS}`,
          [requisitionId, input.variantType, input.content, status, input.basedOnVersionId, auth.userId],
        );
        // Before the first freeze, the requisition follows its review loop (TDD §6.0).
        if (status === 'Revising' && requisition.status === 'PendingApproval') {
          await setRequisitionStatus(db, requisitionId, 'Revising');
        }
        return toDto(rows[0]);
      });
    } catch (err) {
      throw translateDbError(err);
    }
  }

  /** Sends a Draft/Revising version to the manager for approval (-> PendingApproval). */
  async submit(auth: AuthContext, requisitionId: string, versionId: string): Promise<JdVersionDto> {
    return withTenant(this.pool, tenantScopeOf(auth), async (db) => {
      const requisition = await findRequisition(db, requisitionId, true);
      assertOpen(requisition.status);
      const { rows } = await db.query<{ status: VersionStatus }>(
        'SELECT status FROM requisition.jd_version WHERE id = $1 AND requisition_id = $2 FOR UPDATE',
        [versionId, requisitionId],
      );
      if (rows.length === 0) throw notFound('version');
      if (rows[0].status !== 'Draft' && rows[0].status !== 'Revising') {
        throw new ConflictException({
          reason: 'version_not_submittable',
          message: `Only a Draft or Revising version can be sent for approval; this one is ${rows[0].status}.`,
          details: { current_status: rows[0].status },
        });
      }
      const updated = await db.query<JdVersionDto>(
        `UPDATE requisition.jd_version SET status = 'PendingApproval' WHERE id = $1 RETURNING ${VERSION_COLUMNS}`,
        [versionId],
      );
      if (requisition.status === 'Draft' || requisition.status === 'Revising') {
        await setRequisitionStatus(db, requisitionId, 'PendingApproval');
      }
      return toDto(updated.rows[0]);
    });
  }
}

async function findRequisition(db: PoolClient, id: string, lock: boolean): Promise<{ status: string }> {
  const { rows } = await db.query<{ status: string }>(
    `SELECT status FROM requisition.job_requisition WHERE id = $1${lock ? ' FOR UPDATE' : ''}`,
    [id],
  );
  if (rows.length === 0) throw notFound('requisition');
  return rows[0];
}

function assertOpen(status: string): void {
  if (CLOSED_STATES.includes(status)) {
    throw new ConflictException({
      reason: 'requisition_not_editable',
      message: `The requisition is ${status}; its JD can't be changed.`,
      details: { requisition_status: status },
    });
  }
}

async function setRequisitionStatus(db: PoolClient, id: string, status: string): Promise<void> {
  await db.query('UPDATE requisition.job_requisition SET status = $2, updated_at = now() WHERE id = $1', [id, status]);
}

function toDto(row: JdVersionDto): JdVersionDto {
  const createdAt = row.created_at as unknown;
  return { ...row, created_at: createdAt instanceof Date ? createdAt.toISOString() : String(createdAt) };
}

function translateDbError(err: unknown): unknown {
  if ((err as { code?: string }).code === 'TM013') {
    return new UnprocessableEntityException({
      reason: 'unknown_base_version',
      message: 'based_on_version_id is not a version of this requisition.',
    });
  }
  return err;
}
