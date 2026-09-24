// API-layer checks for POST /api/v1/requisitions/intake that must reject before touching the database.
// The org_type rule itself (HR-M1-FR-007) is enforced by the database; see test/db/.
import { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import { AuthContext, configureApp, DB_POOL, ServiceConfig, signAccessToken } from '@teamora/platform';
import request from 'supertest';
import { AppModule } from '../src/app.module';
import { SERVICE } from '../src/service';

const SECRET = 'e2e-test-secret-e2e-test-secret-000001';
const config: ServiceConfig = {
  serviceName: SERVICE.serviceName,
  appEnv: 'test',
  port: 0,
  db: { host: 'unused', port: 5432, database: 'teamora', user: SERVICE.dbRole, password: 'unused' },
  authJwtSecret: SECRET,
};

const TENANT = '0190a1b2-0000-7000-8000-00000000000a';
const manager: AuthContext = { userId: '0190a1b2-0000-7000-8000-000000000001', tenantId: TENANT, role: 'manager' };
const validBody = { tenant_id: TENANT, client_id: null, raw_brief_text: 'Need a data analyst', source: 'portal' };

describe('POST /api/v1/requisitions/intake — request checks', () => {
  let app: INestApplication;
  const connect = jest.fn(() => {
    throw new Error('database must not be reached');
  });

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({ imports: [AppModule.register(config)] })
      .overrideProvider(DB_POOL)
      .useValue({ query: jest.fn(), connect })
      .compile();
    app = configureApp(moduleRef.createNestApplication());
    await app.init();
  });

  afterAll(async () => {
    await app.close();
  });

  afterEach(() => expect(connect).not.toHaveBeenCalled());

  const post = (body: unknown, token?: string) => {
    const req = request(app.getHttpServer()).post('/api/v1/requisitions/intake');
    if (token) req.set('Authorization', `Bearer ${token}`);
    return req.send(body as object);
  };

  it('401 without a token', async () => {
    const res = await post(validBody).expect(401);
    expect(res.body.reason).toBe('missing_token');
  });

  it('401 with a token signed by another key', async () => {
    const res = await post(validBody, signAccessToken('some-other-secret-some-other-secret-01', manager)).expect(401);
    expect(res.body.reason).toBe('invalid_token');
  });

  it('403 when tenant_id is not the caller\'s tenant (TDD §3.1)', async () => {
    const other = { ...validBody, tenant_id: '0190a1b2-0000-7000-8000-00000000000b' };
    const res = await post(other, signAccessToken(SECRET, manager)).expect(403);
    expect(res.body.reason).toBe('tenant_mismatch');
  });

  it('403 for a platform admin (no tenant scope)', async () => {
    const admin: AuthContext = { userId: manager.userId, tenantId: null, role: 'platform_admin' };
    const res = await post(validBody, signAccessToken(SECRET, admin)).expect(403);
    expect(res.body.reason).toBe('tenant_scope_required');
  });

  it('422 when client_id is omitted, even though null would be valid (TDD §5.2)', async () => {
    const { client_id: _omitted, ...withoutClient } = validBody;
    const res = await post(withoutClient, signAccessToken(SECRET, manager)).expect(422);
    expect(res.body).toMatchObject({
      reason: 'validation_failed',
      details: [{ field: 'client_id', problem: 'is required (use null for a direct-employer tenant)' }],
    });
  });

  it('422 listing every invalid field at once', async () => {
    const res = await post(
      { tenant_id: 'nope', client_id: 'also-nope', raw_brief_text: '  ', source: 'fax' },
      signAccessToken(SECRET, manager),
    ).expect(422);
    expect(res.body.details.map((d: { field: string }) => d.field)).toEqual([
      'tenant_id',
      'client_id',
      'raw_brief_text',
      'source',
    ]);
  });

  it('422 for a non-object body', async () => {
    await post([validBody], signAccessToken(SECRET, manager)).expect(422);
  });
});
