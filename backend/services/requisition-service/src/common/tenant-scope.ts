import { ForbiddenException, NotFoundException } from '@nestjs/common';
import { AuthContext, isUuid, TenantScope } from '@teamora/platform';

/** The tenant scope for a request; a platform-admin token has none, so tenant APIs reject it (403). */
export function tenantScopeOf(auth: AuthContext): TenantScope & { tenantId: string } {
  if (auth.tenantId === null) {
    throw new ForbiddenException({
      reason: 'tenant_scope_required',
      message: 'This API works within a tenant; a platform admin token has no tenant scope.',
    });
  }
  return { tenantId: auth.tenantId, clientId: null };
}

/** A path id that isn't a UUID can't identify anything, so it is a 404 rather than a 422. */
export function requireIdParam(value: string, what: 'requisition' | 'version' | 'criterion'): string {
  if (!isUuid(value)) throw notFound(what);
  return value;
}

const NOT_FOUND = {
  requisition: { reason: 'requisition_not_found', message: 'No such requisition in your tenant.' },
  version: { reason: 'version_not_found', message: 'No such JD version on this requisition.' },
  criterion: { reason: 'criterion_not_found', message: 'No such criterion in this matrix.' },
};

export function notFound(what: 'requisition' | 'version' | 'criterion'): NotFoundException {
  return new NotFoundException(NOT_FOUND[what]);
}
