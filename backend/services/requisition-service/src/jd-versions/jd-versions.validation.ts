import { UnprocessableEntityException } from '@nestjs/common';
import { isUuid } from '@teamora/platform';

export const VARIANT_TYPES = ['formal', 'candidate_friendly', 'condensed', 'manager_edited'] as const;
export type VariantType = (typeof VARIANT_TYPES)[number];

/** Upper bound on one JD version's text. */
export const MAX_JD_LENGTH = 50_000;

export interface CreateVersionInput {
  content: string;
  variantType: VariantType;
  /** The version being revised; null for a first draft. */
  basedOnVersionId: string | null;
}

/** Body of POST /requisitions/{id}/jd-versions: `{ content, variant_type?, based_on_version_id? }`. */
export function validateCreateVersion(body: unknown): CreateVersionInput {
  if (typeof body !== 'object' || body === null || Array.isArray(body)) {
    throw invalid([{ field: '(body)', problem: 'must be a JSON object' }]);
  }
  const input = body as Record<string, unknown>;
  const problems: { field: string; problem: string }[] = [];

  const content = input.content;
  if (typeof content !== 'string' || content.trim() === '') {
    problems.push({ field: 'content', problem: 'must be a non-empty string' });
  } else if (content.length > MAX_JD_LENGTH) {
    problems.push({ field: 'content', problem: `must be at most ${MAX_JD_LENGTH} characters` });
  }

  const variantType = input.variant_type ?? 'manager_edited';
  if (!(VARIANT_TYPES as readonly unknown[]).includes(variantType)) {
    problems.push({ field: 'variant_type', problem: `must be one of ${VARIANT_TYPES.join(', ')}` });
  }

  const basedOn = input.based_on_version_id ?? null;
  if (basedOn !== null && !isUuid(basedOn)) {
    problems.push({ field: 'based_on_version_id', problem: 'must be a UUID or null' });
  }

  if (problems.length > 0) throw invalid(problems);
  return { content: content as string, variantType: variantType as VariantType, basedOnVersionId: basedOn as string | null };
}

function invalid(details: { field: string; problem: string }[]): UnprocessableEntityException {
  return new UnprocessableEntityException({ reason: 'validation_failed', message: 'The request body is invalid.', details });
}
