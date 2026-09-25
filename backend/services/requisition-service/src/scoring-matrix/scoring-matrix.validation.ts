import { UnprocessableEntityException } from '@nestjs/common';
import { isUuid } from '@teamora/platform';

/** Screening categories only — soft skills are never scored numerically at this stage (BRD §4.1). */
export const CATEGORIES = ['core_skills', 'experience_seniority', 'domain_competency', 'education_fit'] as const;
export type Category = (typeof CATEGORIES)[number];

export interface WeightEdit {
  criterionId: string;
  weightPercent: number;
}

export interface EditWeightsInput {
  matrixRevision: number;
  criteria: WeightEdit[];
}

export interface AddCriterionInput {
  matrixRevision: number;
  category: Category;
  criterionName: string;
  weightPercent: number;
}

type Problems = { field: string; problem: string }[];

/** PATCH .../scoring-matrix/draft — `{ matrix_revision, criteria: [{ criterion_id, weight_percent }] }` (TDD §8). */
export function validateEditWeights(body: unknown): EditWeightsInput {
  const input = asObject(body);
  const problems: Problems = [];
  const matrixRevision = readRevision(input, problems);
  const criteria: WeightEdit[] = [];
  if (!Array.isArray(input.criteria) || input.criteria.length === 0) {
    problems.push({ field: 'criteria', problem: 'must be a non-empty array' });
  } else {
    input.criteria.forEach((item: unknown, i: number) => {
      const c = (typeof item === 'object' && item !== null ? item : {}) as Record<string, unknown>;
      if (!isUuid(c.criterion_id)) problems.push({ field: `criteria[${i}].criterion_id`, problem: 'must be a UUID' });
      checkWeight(c.weight_percent, `criteria[${i}].weight_percent`, problems);
      criteria.push({ criterionId: c.criterion_id as string, weightPercent: c.weight_percent as number });
    });
    const ids = criteria.map((c) => c.criterionId);
    if (new Set(ids).size !== ids.length) problems.push({ field: 'criteria', problem: 'must not repeat a criterion_id' });
  }
  if (problems.length > 0) throw invalid(problems);
  return { matrixRevision, criteria };
}

/** POST .../scoring-matrix/draft/criteria — `{ matrix_revision, category, criterion_name, weight_percent }`. */
export function validateAddCriterion(body: unknown): AddCriterionInput {
  const input = asObject(body);
  const problems: Problems = [];
  const matrixRevision = readRevision(input, problems);
  if (!(CATEGORIES as readonly unknown[]).includes(input.category)) {
    problems.push({ field: 'category', problem: `must be one of ${CATEGORIES.join(', ')}` });
  }
  const name = input.criterion_name;
  if (typeof name !== 'string' || name.trim() === '' || name.length > 200) {
    problems.push({ field: 'criterion_name', problem: 'must be a non-empty string of at most 200 characters' });
  }
  checkWeight(input.weight_percent, 'weight_percent', problems);
  if (problems.length > 0) throw invalid(problems);
  return {
    matrixRevision,
    category: input.category as Category,
    criterionName: (name as string).trim(),
    weightPercent: input.weight_percent as number,
  };
}

/** `?matrix_revision=N` on DELETE .../criteria/{criterionId}. */
export function parseRevisionQuery(value: unknown): number {
  const n = Number(value);
  if (!Number.isInteger(n) || n < 1) {
    throw invalid([{ field: 'matrix_revision', problem: 'query parameter must be a positive integer' }]);
  }
  return n;
}

function asObject(body: unknown): Record<string, unknown> {
  if (typeof body !== 'object' || body === null || Array.isArray(body)) {
    throw invalid([{ field: '(body)', problem: 'must be a JSON object' }]);
  }
  return body as Record<string, unknown>;
}

function readRevision(input: Record<string, unknown>, problems: Problems): number {
  const r = input.matrix_revision;
  if (!Number.isInteger(r) || (r as number) < 1) {
    problems.push({ field: 'matrix_revision', problem: 'must be a positive integer (the revision you last read)' });
  }
  return r as number;
}

/** Per-criterion bounds: 0-100 with at most two decimals. The total is checked only at freeze. */
function checkWeight(value: unknown, field: string, problems: Problems): void {
  // Compare with a tolerance: 33.33 * 100 is 3332.9999999999995 in floating point.
  const twoDecimals = (v: number) => Math.abs(Math.round(v * 100) - v * 100) < 1e-6;
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 100 || !twoDecimals(value)) {
    problems.push({ field, problem: 'must be a number from 0 to 100 with at most two decimals' });
  }
}

function invalid(details: Problems): UnprocessableEntityException {
  return new UnprocessableEntityException({ reason: 'validation_failed', message: 'The request body is invalid.', details });
}
