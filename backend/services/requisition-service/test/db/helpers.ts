// Shared setup for requisition-service database tests.
import { randomUUID } from 'node:crypto';
import { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import { AuthContext, configureApp, ServiceConfig, signAccessToken, withTenant } from '@teamora/platform';
import { Pool } from 'pg';
import request from 'supertest';
import { AppModule } from '../../src/app.module';
import { SERVICE } from '../../src/service';

export const SECRET = 'db-test-secret-db-test-secret-0000001';
const host = process.env.POSTGRES_HOST ?? 'localhost';
const port = Number(process.env.POSTGRES_PORT ?? 5432);

export const identityPool = (): Pool =>
  new Pool({ host, port, database: 'teamora', user: 'svc_auth', password: process.env.POSTGRES_SVC_AUTH_PASSWORD, max: 2 });

export const requisitionPool = (): Pool =>
  new Pool({
    host, port, database: 'teamora', user: 'svc_requisition', password: process.env.POSTGRES_SVC_REQUISITION_PASSWORD, max: 4,
  });

export async function startApp(): Promise<INestApplication> {
  const config: ServiceConfig = {
    serviceName: SERVICE.serviceName,
    appEnv: 'test',
    port: 0,
    db: { host, port, database: 'teamora', user: 'svc_requisition', password: process.env.POSTGRES_SVC_REQUISITION_PASSWORD ?? '' },
    authJwtSecret: SECRET,
  };
  const moduleRef = await Test.createTestingModule({ imports: [AppModule.register(config)] }).compile();
  const app = configureApp(moduleRef.createNestApplication());
  await app.init();
  return app;
}

export async function createTenant(pool: Pool, orgType: 'direct_employer' | 'staffing_agency'): Promise<string> {
  const id = randomUUID();
  await withTenant(pool, { tenantId: id, clientId: null }, (db) =>
    db.query('INSERT INTO identity.tenant (id, org_type, name) VALUES ($1, $2, $3)', [id, orgType, `${orgType} ${id}`]),
  );
  return id;
}

export async function createClient(pool: Pool, tenantId: string): Promise<string> {
  return withTenant(pool, { tenantId, clientId: null }, async (db) => {
    const { rows } = await db.query<{ id: string }>(
      "INSERT INTO identity.client (agency_tenant_id, name) VALUES ($1, 'End client') RETURNING id",
      [tenantId],
    );
    return rows[0].id;
  });
}

export const managerOf = (tenantId: string): AuthContext => ({ userId: randomUUID(), tenantId, role: 'manager' });

/** An authenticated supertest agent for one caller. */
export function api(app: INestApplication, auth: AuthContext) {
  const token = `Bearer ${signAccessToken(SECRET, auth)}`;
  const server = app.getHttpServer();
  return {
    get: (url: string) => request(server).get(url).set('Authorization', token),
    post: (url: string, body?: object) => request(server).post(url).set('Authorization', token).send(body ?? {}),
    patch: (url: string, body?: object) => request(server).patch(url).set('Authorization', token).send(body ?? {}),
  };
}

/** Creates a direct-employer requisition through the intake API and returns its id. */
export async function createRequisition(app: INestApplication, auth: AuthContext): Promise<string> {
  const res = await api(app, auth)
    .post('/api/v1/requisitions/intake', {
      tenant_id: auth.tenantId,
      client_id: null,
      raw_brief_text: 'Data analyst, Power BI',
      source: 'portal',
    })
    .expect(201);
  return res.body.requisition_id;
}
