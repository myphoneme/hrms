// HR-M1-FR-007 acceptance scenarios (BRD §4.1) and requisition isolation, against a real bootstrapped
// and migrated `teamora` database. The API runs as svc_requisition; test tenants are seeded as svc_auth.
// Required env: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_SVC_AUTH_PASSWORD, POSTGRES_SVC_REQUISITION_PASSWORD.
import { randomUUID } from 'node:crypto';
import { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import { AuthContext, configureApp, ServiceConfig, signAccessToken, withTenant } from '@teamora/platform';
import { Pool } from 'pg';
import request from 'supertest';
import { AppModule } from '../../src/app.module';
import { SERVICE } from '../../src/service';

const SECRET = 'db-test-secret-db-test-secret-0000001';
const host = process.env.POSTGRES_HOST ?? 'localhost';
const port = Number(process.env.POSTGRES_PORT ?? 5432);

const config: ServiceConfig = {
  serviceName: SERVICE.serviceName,
  appEnv: 'test',
  port: 0,
  db: { host, port, database: 'teamora', user: 'svc_requisition', password: process.env.POSTGRES_SVC_REQUISITION_PASSWORD ?? '' },
  authJwtSecret: SECRET,
};

const identityPool = new Pool({
  host, port, database: 'teamora', user: 'svc_auth', password: process.env.POSTGRES_SVC_AUTH_PASSWORD, max: 2,
});
const requisitionPool = new Pool({
  host, port, database: 'teamora', user: 'svc_requisition', password: process.env.POSTGRES_SVC_REQUISITION_PASSWORD, max: 2,
});

async function createTenant(orgType: 'direct_employer' | 'staffing_agency'): Promise<string> {
  const id = randomUUID();
  await withTenant(identityPool, { tenantId: id, clientId: null }, (db) =>
    db.query('INSERT INTO identity.tenant (id, org_type, name) VALUES ($1, $2, $3)', [id, orgType, `${orgType} ${id}`]),
  );
  return id;
}

async function createClient(tenantId: string): Promise<string> {
  return withTenant(identityPool, { tenantId, clientId: null }, async (db) => {
    const { rows } = await db.query<{ id: string }>(
      "INSERT INTO identity.client (agency_tenant_id, name) VALUES ($1, 'End client') RETURNING id",
      [tenantId],
    );
    return rows[0].id;
  });
}

const managerOf = (tenantId: string): AuthContext => ({ userId: randomUUID(), tenantId, role: 'manager' });

describe('HR-M1-FR-007 — staffing-agency / multi-client requisitions', () => {
  let app: INestApplication;
  let agency: string;
  let agencyClient: string;
  let otherAgency: string;
  let otherAgencyClient: string;
  let employer: string;

  beforeAll(async () => {
    agency = await createTenant('staffing_agency');
    agencyClient = await createClient(agency);
    otherAgency = await createTenant('staffing_agency');
    otherAgencyClient = await createClient(otherAgency);
    employer = await createTenant('direct_employer');

    const moduleRef = await Test.createTestingModule({ imports: [AppModule.register(config)] }).compile();
    app = configureApp(moduleRef.createNestApplication());
    await app.init();
  });

  afterAll(async () => {
    await app.close();
    await identityPool.end();
    await requisitionPool.end();
  });

  const intake = (auth: AuthContext, body: Record<string, unknown>) =>
    request(app.getHttpServer())
      .post('/api/v1/requisitions/intake')
      .set('Authorization', `Bearer ${signAccessToken(SECRET, auth)}`)
      .send({ tenant_id: auth.tenantId, raw_brief_text: 'Senior data analyst, Power BI, 5+ years', source: 'portal', ...body });

  const readRequisition = (tenantId: string, id: string) =>
    withTenant(requisitionPool, { tenantId, clientId: null }, async (db) => {
      const { rows } = await db.query(
        `SELECT r.tenant_id, r.client_id, r.status, r.created_by, b.raw_text, b.source
           FROM requisition.job_requisition r JOIN requisition.jd_brief b ON b.requisition_id = r.id
          WHERE r.id = $1`,
        [id],
      );
      return rows[0];
    });

  // BRD §4.1 acceptance scenario: agency manager submits a brief without selecting a client.
  it('rejects an agency brief without a client (422 client_required)', async () => {
    const res = await intake(managerOf(agency), { client_id: null }).expect(422);
    expect(res.body.reason).toBe('client_required');
  });

  // BRD §4.1 acceptance scenario: direct-employer manager submits a brief with a client selected.
  it('rejects a direct-employer brief with a client (422 client_not_allowed)', async () => {
    const res = await intake(managerOf(employer), { client_id: agencyClient }).expect(422);
    expect(res.body.reason).toBe('client_not_allowed');
  });

  it('creates a Draft requisition and its brief for an agency with its own client', async () => {
    const auth = managerOf(agency);
    const res = await intake(auth, { client_id: agencyClient }).expect(201);
    expect(res.body).toEqual({ requisition_id: expect.any(String), status: 'Draft' });
    expect(await readRequisition(agency, res.body.requisition_id)).toEqual({
      tenant_id: agency,
      client_id: agencyClient,
      status: 'Draft',
      created_by: auth.userId,
      raw_text: 'Senior data analyst, Power BI, 5+ years',
      source: 'portal',
    });
  });

  it('creates a Draft requisition for a direct employer with client_id: null', async () => {
    const res = await intake(managerOf(employer), { client_id: null, source: 'email' }).expect(201);
    expect(await readRequisition(employer, res.body.requisition_id)).toMatchObject({ client_id: null, source: 'email' });
  });

  it("rejects an agency brief naming another agency's client (422 unknown_client)", async () => {
    const res = await intake(managerOf(agency), { client_id: otherAgencyClient }).expect(422);
    expect(res.body.reason).toBe('unknown_client');
  });

  it("rejects a client id that doesn't exist (422 unknown_client)", async () => {
    const res = await intake(managerOf(agency), { client_id: randomUUID() }).expect(422);
    expect(res.body.reason).toBe('unknown_client');
  });

  it('writes nothing when a brief is rejected', async () => {
    const before = await countRequisitions(agency);
    await intake(managerOf(agency), { client_id: null }).expect(422);
    expect(await countRequisitions(agency)).toBe(before);
  });

  it('enforces the rule in the database even without the API (defense in depth)', async () => {
    await expect(
      withTenant(requisitionPool, { tenantId: agency, clientId: null }, (db) =>
        db.query('INSERT INTO requisition.job_requisition (tenant_id, client_id, created_by) VALUES ($1, NULL, $2)', [
          agency,
          randomUUID(),
        ]),
      ),
    ).rejects.toMatchObject({ code: 'TM001' });
  });

  it("never shows one tenant another tenant's requisitions", async () => {
    const res = await intake(managerOf(agency), { client_id: agencyClient }).expect(201);
    expect(await readRequisition(otherAgency, res.body.requisition_id)).toBeUndefined();
    expect(await readRequisition(employer, res.body.requisition_id)).toBeUndefined();
    const db = await requisitionPool.connect();
    try {
      const { rows } = await db.query('SELECT count(*)::int AS n FROM requisition.job_requisition');
      expect(rows[0].n).toBe(0); // no tenant scope -> zero rows
    } finally {
      db.release();
    }
  });

  it('scopes to one client when the request is client-scoped', async () => {
    const res = await intake(managerOf(agency), { client_id: agencyClient }).expect(201);
    const seenByOtherClientScope = await withTenant(
      requisitionPool,
      { tenantId: agency, clientId: randomUUID() },
      async (db) => (await db.query('SELECT 1 FROM requisition.job_requisition WHERE id = $1', [res.body.requisition_id])).rowCount,
    );
    expect(seenByOtherClientScope).toBe(0);
  });

  async function countRequisitions(tenantId: string): Promise<number> {
    return withTenant(requisitionPool, { tenantId, clientId: null }, async (db) => {
      const { rows } = await db.query<{ n: number }>('SELECT count(*)::int AS n FROM requisition.job_requisition');
      return rows[0].n;
    });
  }
});
