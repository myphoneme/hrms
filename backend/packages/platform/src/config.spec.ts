import { ConfigError, loadServiceConfig, ServiceDefinition } from './config';

const def: ServiceDefinition = {
  serviceName: 'auth-service',
  defaultPort: 3001,
  dbRole: 'svc_auth',
  dbPasswordVar: 'POSTGRES_SVC_AUTH_PASSWORD',
};

const validEnv = {
  APP_ENV: 'local',
  POSTGRES_HOST: 'localhost',
  POSTGRES_SVC_AUTH_PASSWORD: 'local-password-123',
};

describe('loadServiceConfig', () => {
  it('builds the config from environment variables, logging in as the service role', () => {
    const config = loadServiceConfig(def, { ...validEnv });
    expect(config).toEqual({
      serviceName: 'auth-service',
      appEnv: 'local',
      port: 3001,
      db: { host: 'localhost', port: 5432, database: 'teamora', user: 'svc_auth', password: 'local-password-123' },
    });
  });

  it('uses PORT and POSTGRES_PORT when set', () => {
    const config = loadServiceConfig(def, { ...validEnv, PORT: '4001', POSTGRES_PORT: '5433' });
    expect(config.port).toBe(4001);
    expect(config.db.port).toBe(5433);
  });

  it('reports every missing variable at once', () => {
    expect(() => loadServiceConfig(def, {})).toThrow(ConfigError);
    try {
      loadServiceConfig(def, {});
    } catch (err) {
      const message = (err as Error).message;
      expect(message).toContain('APP_ENV is not set');
      expect(message).toContain('POSTGRES_HOST is not set');
      expect(message).toContain('POSTGRES_SVC_AUTH_PASSWORD is not set');
    }
  });

  it('rejects an unknown APP_ENV', () => {
    expect(() => loadServiceConfig(def, { ...validEnv, APP_ENV: 'dev' })).toThrow(/APP_ENV must be one of/);
  });

  it('rejects any database name other than teamora', () => {
    expect(() => loadServiceConfig(def, { ...validEnv, POSTGRES_DB: 'teamora_dev' })).toThrow(
      /POSTGRES_DB must be "teamora"/,
    );
  });

  it('rejects an invalid port', () => {
    expect(() => loadServiceConfig(def, { ...validEnv, PORT: 'abc' })).toThrow(/PORT must be a port number/);
  });
});
