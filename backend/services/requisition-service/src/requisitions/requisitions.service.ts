import { ForbiddenException, Inject, Injectable, UnprocessableEntityException } from '@nestjs/common';
import { DB_POOL, withTenant } from '@teamora/platform';
import { Pool } from 'pg';
import { IntakeCommand } from './intake.validation';

export interface IntakeResult {
  requisition_id: string;
  status: 'Draft';
}

interface PgError {
  code?: string;
  constraint?: string;
}

@Injectable()
export class RequisitionsService {
  constructor(@Inject(DB_POOL) private readonly pool: Pool) {}

  /** Creates a Draft JobRequisition and its raw JDBrief in one transaction (TDD §12.1 step 2). */
  async createFromIntake(cmd: IntakeCommand): Promise<IntakeResult> {
    try {
      return await withTenant(this.pool, { tenantId: cmd.tenantId, clientId: null }, async (db) => {
        const { rows } = await db.query<{ id: string }>(
          `INSERT INTO requisition.job_requisition (tenant_id, client_id, department_id, created_by)
           VALUES ($1, $2, $3, $4) RETURNING id`,
          [cmd.tenantId, cmd.clientId, cmd.departmentId, cmd.createdBy],
        );
        const requisitionId = rows[0].id;
        await db.query('INSERT INTO requisition.jd_brief (requisition_id, raw_text, source) VALUES ($1, $2, $3)', [
          requisitionId,
          cmd.rawBriefText,
          cmd.source,
        ]);
        return { requisition_id: requisitionId, status: 'Draft' as const };
      });
    } catch (err) {
      throw translateDbError(err as PgError);
    }
  }
}

/** Maps the database's HR-M1-FR-007 and isolation rejections to API errors; anything else is a 500. */
function translateDbError(err: PgError): unknown {
  switch (err.code) {
    case 'TM001':
      return new UnprocessableEntityException({
        reason: 'client_required',
        message: 'This tenant is a staffing agency: the requisition must specify the end-client (client_id).',
      });
    case 'TM002':
      return new UnprocessableEntityException({
        reason: 'client_not_allowed',
        message: 'This tenant is a direct employer: client_id must be null.',
      });
    case '23503':
      if (err.constraint === 'job_requisition_client_fkey') {
        return new UnprocessableEntityException({
          reason: 'unknown_client',
          message: 'client_id does not identify a client of this tenant.',
        });
      }
      if (err.constraint === 'job_requisition_tenant_fkey') {
        return new ForbiddenException({ reason: 'unknown_tenant', message: 'The caller\'s tenant does not exist.' });
      }
      return err;
    default:
      return err;
  }
}
