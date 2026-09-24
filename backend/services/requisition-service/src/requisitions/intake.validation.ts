import { ForbiddenException, UnprocessableEntityException } from '@nestjs/common';
import { AuthContext, isUuid } from '@teamora/platform';

export const BRIEF_SOURCES = ['email', 'portal'] as const;
export type BriefSource = (typeof BRIEF_SOURCES)[number];

/** Upper bound on a raw brief, so a single request can't store an unbounded text blob. */
export const MAX_BRIEF_LENGTH = 20_000;

/** A validated POST /api/v1/requisitions/intake request (TDD §8). */
export interface IntakeCommand {
  tenantId: string;
  clientId: string | null;
  departmentId: string | null;
  rawBriefText: string;
  source: BriefSource;
  createdBy: string;
}

interface FieldProblem {
  field: string;
  problem: string;
}

/**
 * Checks request shape and caller scope. Whether client_id is required or forbidden depends on the
 * tenant's org_type, which the database enforces (HR-M1-FR-007) — this layer only guarantees the
 * field is *present* (absent vs. explicit null, TDD §5.2) and well-formed.
 */
export function validateIntake(body: unknown, auth: AuthContext): IntakeCommand {
  if (auth.tenantId === null) {
    throw new ForbiddenException({
      reason: 'tenant_scope_required',
      message: 'Requisitions are created within a tenant; a platform admin token has no tenant scope.',
    });
  }
  if (typeof body !== 'object' || body === null || Array.isArray(body)) {
    throw invalid([{ field: '(body)', problem: 'must be a JSON object' }]);
  }
  const input = body as Record<string, unknown>;
  const problems: FieldProblem[] = [];

  if (!isUuid(input.tenant_id)) problems.push({ field: 'tenant_id', problem: 'must be a UUID' });

  // Omitting client_id is always a validation error, for every org_type; null is a valid value (TDD §5.2).
  if (!('client_id' in input)) {
    problems.push({ field: 'client_id', problem: 'is required (use null for a direct-employer tenant)' });
  } else if (input.client_id !== null && !isUuid(input.client_id)) {
    problems.push({ field: 'client_id', problem: 'must be a UUID or null' });
  }

  if (input.department_id !== undefined && input.department_id !== null && !isUuid(input.department_id)) {
    problems.push({ field: 'department_id', problem: 'must be a UUID or null' });
  }

  const text = input.raw_brief_text;
  if (typeof text !== 'string' || text.trim() === '') {
    problems.push({ field: 'raw_brief_text', problem: 'must be a non-empty string' });
  } else if (text.length > MAX_BRIEF_LENGTH) {
    problems.push({ field: 'raw_brief_text', problem: `must be at most ${MAX_BRIEF_LENGTH} characters` });
  }

  if (!(BRIEF_SOURCES as readonly unknown[]).includes(input.source)) {
    problems.push({ field: 'source', problem: `must be one of ${BRIEF_SOURCES.join(', ')}` });
  }

  if (problems.length > 0) throw invalid(problems);

  // Every token carries tenant_id; a request for any other tenant is rejected (TDD §3.1).
  if (input.tenant_id !== auth.tenantId) {
    throw new ForbiddenException({
      reason: 'tenant_mismatch',
      message: "tenant_id does not match the caller's tenant.",
    });
  }

  return {
    tenantId: auth.tenantId,
    clientId: (input.client_id as string | null) ?? null,
    departmentId: (input.department_id as string | null | undefined) ?? null,
    rawBriefText: text as string,
    source: input.source as BriefSource,
    createdBy: auth.userId,
  };
}

function invalid(details: FieldProblem[]): UnprocessableEntityException {
  return new UnprocessableEntityException({
    reason: 'validation_failed',
    message: 'The request body is invalid.',
    details,
  });
}
