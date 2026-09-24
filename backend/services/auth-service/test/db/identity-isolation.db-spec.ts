// Runs against a real, bootstrapped and migrated `teamora` database, logged in as svc_auth.
// Required env: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_SVC_AUTH_PASSWORD (see backend/README.md).
import { randomUUID } from 'node:crypto';
import { Pool } from 'pg';
import { withTenant } from '@teamora/platform';

const pool = new Pool({
  host: process.env.POSTGRES_HOST,
  port: Number(process.env.POSTGRES_PORT ?? 5432),
  database: 'teamora',
  user: 'svc_auth',
  password: process.env.POSTGRES_SVC_AUTH_PASSWORD,
  max: 4,
});

type OrgType = 'direct_employer' | 'staffing_agency';

async function createTenant(orgType: OrgType, name: string): Promise<string> {
  const id = randomUUID();
  await withTenant(pool, { tenantId: id, clientId: null }, (db) =>
    db.query('INSERT INTO identity.tenant (id, org_type, name) VALUES ($1, $2, $3)', [id, orgType, name]),
  );
  return id;
}

async function createClient(tenantId: string, name: string): Promise<string> {
  return withTenant(pool, { tenantId, clientId: null }, async (db) => {
    const { rows } = await db.query<{ id: string }>(
      'INSERT INTO identity.client (agency_tenant_id, name) VALUES ($1, $2) RETURNING id',
      [tenantId, name],
    );
    return rows[0].id;
  });
}

async function createUser(tenantId: string, email: string): Promise<void> {
  await withTenant(pool, { tenantId, clientId: null }, (db) =>
    db.query(
      "INSERT INTO identity.app_user (tenant_id, email, auth_method, role) VALUES ($1, $2, 'sso_google', 'manager')",
      [tenantId, email],
    ),
  );
}

async function countVisible(scopeTenantId: string, table: string): Promise<number> {
  return withTenant(pool, { tenantId: scopeTenantId, clientId: null }, async (db) => {
    const { rows } = await db.query<{ n: string }>(`SELECT count(*) AS n FROM identity.${table}`);
    return Number(rows[0].n);
  });
}

describe('identity schema: tenant isolation (TDD §5.3, BRD §5)', () => {
  let agencyA: string;
  let agencyB: string;
  let employer: string;

  beforeAll(async () => {
    agencyA = await createTenant('staffing_agency', 'Agency A');
    agencyB = await createTenant('staffing_agency', 'Agency B');
    employer = await createTenant('direct_employer', 'Direct Employer');
    await createClient(agencyA, 'Client of A');
    await createClient(agencyB, 'Client of B');
    await createUser(agencyA, 'manager@agency-a.test');
    await createUser(agencyB, 'manager@agency-b.test');
  });

  afterAll(async () => {
    await pool.end();
  });

  it('shows nothing without a tenant scope', async () => {
    const db = await pool.connect();
    try {
      for (const table of ['tenant', 'client', 'app_user']) {
        const { rows } = await db.query<{ n: string }>(`SELECT count(*) AS n FROM identity.${table}`);
        expect(Number(rows[0].n)).toBe(0);
      }
    } finally {
      db.release();
    }
  });

  it("shows a tenant only its own tenant row, clients and users", async () => {
    expect(await countVisible(agencyA, 'tenant')).toBe(1);
    expect(await countVisible(agencyA, 'client')).toBe(1);
    expect(await countVisible(agencyA, 'app_user')).toBe(1);
    const names = await withTenant(pool, { tenantId: agencyA, clientId: null }, async (db) => {
      const { rows } = await db.query<{ name: string }>('SELECT name FROM identity.client');
      return rows.map((r) => r.name);
    });
    expect(names).toEqual(['Client of A']);
  });

  it("cannot read another tenant's rows by id", async () => {
    const { rows } = await withTenant(pool, { tenantId: agencyA, clientId: null }, (db) =>
      db.query('SELECT id FROM identity.tenant WHERE id = $1', [agencyB]),
    );
    expect(rows).toHaveLength(0);
  });

  it("cannot write rows into another tenant", async () => {
    await expect(
      withTenant(pool, { tenantId: agencyA, clientId: null }, (db) =>
        db.query('INSERT INTO identity.client (agency_tenant_id, name) VALUES ($1, $2)', [agencyB, 'Sneaky']),
      ),
    ).rejects.toThrow(/row-level security/);
    await expect(
      withTenant(pool, { tenantId: agencyA, clientId: null }, (db) =>
        db.query("UPDATE identity.client SET name = 'Hijacked' WHERE agency_tenant_id = $1", [agencyB]),
      ),
    ).resolves.toMatchObject({ rowCount: 0 });
  });

  it('rejects a client under a direct-employer tenant', async () => {
    await expect(createClient(employer, 'Not allowed')).rejects.toMatchObject({ code: 'TM003' });
  });

  it("does not allow changing a tenant's org_type", async () => {
    await expect(
      withTenant(pool, { tenantId: employer, clientId: null }, (db) =>
        db.query("UPDATE identity.tenant SET org_type = 'staffing_agency' WHERE id = $1", [employer]),
      ),
    ).rejects.toMatchObject({ code: 'TM004' });
  });

  it('keeps email unique within a tenant but not across tenants', async () => {
    await expect(createUser(agencyA, 'MANAGER@agency-a.test')).rejects.toMatchObject({ code: '23505' });
    await expect(createUser(agencyB, 'manager@agency-a.test')).resolves.toBeUndefined();
  });

  it('allows a password hash only for local-password users', async () => {
    await expect(
      withTenant(pool, { tenantId: agencyA, clientId: null }, (db) =>
        db.query(
          "INSERT INTO identity.app_user (tenant_id, email, auth_method, password_hash, role) VALUES ($1, 'sso@a.test', 'sso_google', 'x', 'manager')",
          [agencyA],
        ),
      ),
    ).rejects.toMatchObject({ code: '23514' });
  });

  it('does not let svc_auth see or change the migration history', async () => {
    const db = await pool.connect();
    try {
      await expect(db.query('SELECT * FROM identity.schema_migrations')).rejects.toThrow(/permission denied/);
    } finally {
      db.release();
    }
  });
});
