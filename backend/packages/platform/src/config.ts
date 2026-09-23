export const APP_ENVS = ['local', 'test', 'staging', 'production'] as const;
export type AppEnv = (typeof APP_ENVS)[number];

/** Same database name in every environment; only credentials change (Technical Stack Charter v1.1, Database rules 3). */
export const DATABASE_NAME = 'teamora';

export interface DatabaseConfig {
  host: string;
  port: number;
  database: string;
  user: string;
  password: string;
}

export interface ServiceConfig {
  serviceName: string;
  appEnv: AppEnv;
  port: number;
  db: DatabaseConfig;
}

export interface ServiceDefinition {
  serviceName: string;
  defaultPort: number;
  /** Login role created by backend/db/init, e.g. `svc_auth`. */
  dbRole: string;
  /** Environment variable holding that role's password, e.g. `POSTGRES_SVC_AUTH_PASSWORD`. */
  dbPasswordVar: string;
}

export class ConfigError extends Error {}

/**
 * Reads a service's configuration from environment variables. The variable names are the same in
 * every environment: a local backend/.env on developer machines, Coolify variables on staging/production.
 * Collects every problem before failing, so a misconfigured deploy reports all of them at once.
 */
export function loadServiceConfig(def: ServiceDefinition, env: NodeJS.ProcessEnv = process.env): ServiceConfig {
  const problems: string[] = [];
  const required = (name: string): string => {
    const value = env[name]?.trim();
    if (!value) problems.push(`${name} is not set`);
    return value ?? '';
  };

  const appEnv = required('APP_ENV');
  if (appEnv && !(APP_ENVS as readonly string[]).includes(appEnv)) {
    problems.push(`APP_ENV must be one of ${APP_ENVS.join(', ')} (got "${appEnv}")`);
  }
  const host = required('POSTGRES_HOST');
  const password = required(def.dbPasswordVar);
  const database = env.POSTGRES_DB?.trim() || DATABASE_NAME;
  if (database !== DATABASE_NAME) {
    problems.push(`POSTGRES_DB must be "${DATABASE_NAME}" in every environment (got "${database}")`);
  }
  const port = parsePort('PORT', env.PORT, def.defaultPort, problems);
  const dbPort = parsePort('POSTGRES_PORT', env.POSTGRES_PORT, 5432, problems);

  if (problems.length > 0) {
    throw new ConfigError(`${def.serviceName}: invalid configuration:\n  - ${problems.join('\n  - ')}`);
  }

  return {
    serviceName: def.serviceName,
    appEnv: appEnv as AppEnv,
    port,
    db: { host, port: dbPort, database, user: def.dbRole, password },
  };
}

function parsePort(name: string, raw: string | undefined, fallback: number, problems: string[]): number {
  if (raw === undefined || raw.trim() === '') return fallback;
  const value = Number(raw);
  if (!Number.isInteger(value) || value < 1 || value > 65535) {
    problems.push(`${name} must be a port number (got "${raw}")`);
    return fallback;
  }
  return value;
}
