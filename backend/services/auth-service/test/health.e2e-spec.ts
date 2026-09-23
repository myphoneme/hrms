import { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import { configureApp, DB_POOL, ServiceConfig } from '@teamora/platform';
import request from 'supertest';
import { AppModule } from '../src/app.module';
import { SERVICE } from '../src/service';

const config: ServiceConfig = {
  serviceName: SERVICE.serviceName,
  appEnv: 'test',
  port: 0,
  db: { host: 'unused', port: 5432, database: 'teamora', user: SERVICE.dbRole, password: 'unused' },
};

describe(`${SERVICE.serviceName} health endpoints`, () => {
  let app: INestApplication;
  const query = jest.fn();

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({ imports: [AppModule.register(config)] })
      .overrideProvider(DB_POOL)
      .useValue({ query })
      .compile();
    app = configureApp(moduleRef.createNestApplication());
    await app.init();
  });

  afterAll(async () => {
    await app.close();
  });

  it('GET /health returns 200 without touching the database', async () => {
    query.mockClear();
    await request(app.getHttpServer())
      .get('/health')
      .expect(200, { status: 'ok', service: SERVICE.serviceName, appEnv: 'test' });
    expect(query).not.toHaveBeenCalled();
  });

  it('GET /health/ready returns 200 when the database answers', async () => {
    query.mockResolvedValueOnce({ rows: [{ '?column?': 1 }] });
    await request(app.getHttpServer())
      .get('/health/ready')
      .expect(200, { status: 'ok', service: SERVICE.serviceName, checks: { database: 'up' } });
  });

  it('GET /health/ready returns 503 without error details when the database is down', async () => {
    query.mockRejectedValueOnce(new Error('connect ECONNREFUSED 10.0.0.1:5432 user svc_auth'));
    const res = await request(app.getHttpServer()).get('/health/ready').expect(503);
    expect(res.body).toEqual({ status: 'error', service: SERVICE.serviceName, checks: { database: 'down' } });
    expect(JSON.stringify(res.body)).not.toContain('ECONNREFUSED');
  });

  it('keeps health outside the /api/v1 prefix', async () => {
    await request(app.getHttpServer()).get('/api/v1/health').expect(404);
  });
});
