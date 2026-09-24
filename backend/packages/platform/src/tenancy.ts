import { Pool, PoolClient } from 'pg';

/** The (tenant, client) scope every multi-tenant query runs under (TDD §5.2). */
export interface TenantScope {
  tenantId: string;
  /** Explicitly null for a direct-employer tenant or when a request is not client-scoped. */
  clientId: string | null;
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isUuid(value: unknown): value is string {
  return typeof value === 'string' && UUID.test(value);
}

/**
 * Runs `fn` in one transaction with the tenant scope set as transaction-local settings
 * (`app.tenant_id`, `app.client_id`). Every multi-tenant table's Row-Level Security policy reads
 * these; a connection without them sees zero rows (TDD §5.3). This is the only way service code
 * should query multi-tenant tables.
 */
export async function withTenant<T>(pool: Pool, scope: TenantScope, fn: (db: PoolClient) => Promise<T>): Promise<T> {
  if (!isUuid(scope.tenantId)) throw new Error('withTenant: tenantId must be a UUID');
  if (scope.clientId !== null && !isUuid(scope.clientId)) throw new Error('withTenant: clientId must be a UUID or null');

  const db = await pool.connect();
  try {
    await db.query('BEGIN');
    await db.query("SELECT set_config('app.tenant_id', $1, true), set_config('app.client_id', $2, true)", [
      scope.tenantId,
      scope.clientId ?? '',
    ]);
    const result = await fn(db);
    await db.query('COMMIT');
    return result;
  } catch (err) {
    await db.query('ROLLBACK').catch(() => undefined);
    throw err;
  } finally {
    db.release();
  }
}
