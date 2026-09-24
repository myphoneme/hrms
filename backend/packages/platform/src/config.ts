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
  /** HS256 key used to verify access tokens (TDD §3.3); at least 32 characters. */
  authJwtSecret: string;
}

/** Login role that owns every schema and is the only role that runs migrations (backend/db/init). */
export const MIGRATOR_ROLE = 'teamora_migrator';

const MIN_JWT_SECRET_LENGTH = 32;

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
  const required = requiredReader(env, problems);

  const appEnv = readAppEnv(required, problems);
  const db = readDatabase(env, required, problems, def.dbRole, def.dbPasswordVar);
  const authJwtSecret = required('AUTH_JWT_SECRET');
  if (authJwtSecret && authJwtSecret.length < MIN_JWT_SECRET_LENGTH) {
    problems.push(`AUTH_JWT_SECRET must be at least ${MIN_JWT_SECRET_LENGTH} characters`);
  }
  const port = parsePort('PORT', env.PORT, def.defaultPort, problems);

  if (problems.length > 0) {
    throw new ConfigError(`${def.serviceName}: invalid configuration:\n  - ${problems.join('\n  - ')}`);
  }
  return { serviceName: def.serviceName, appEnv, port, db, authJwtSecret };
}

/** Connection settings for running migrations as teamora_migrator (never used by a running service). */
export function loadMigratorConfig(env: NodeJS.ProcessEnv = process.env): DatabaseConfig {
  const problems: string[] = [];
  const required = requiredReader(env, problems);
  readAppEnv(required, problems);
  const db = readDatabase(env, required, problems, MIGRATOR_ROLE, 'POSTGRES_MIGRATOR_PASSWORD');
  if (problems.length > 0) {
    throw new ConfigError(`migrations: invalid configuration:\n  - ${problems.join('\n  - ')}`);
  }
  return db;
}

function requiredReader(env: NodeJS.ProcessEnv, problems: string[]) {
  return (name: string): string => {
    const value = env[name]?.trim();
    if (!value) problems.push(`${name} is not set`);
    return value ?? '';
  };
}

function readAppEnv(required: (name: string) => string, problems: string[]): AppEnv {
  const appEnv = required('APP_ENV');
  if (appEnv && !(APP_ENVS as readonly string[]).includes(appEnv)) {
    problems.push(`APP_ENV must be one of ${APP_ENVS.join(', ')} (got "${appEnv}")`);
  }
  return appEnv as AppEnv;
}

function readDatabase(
  env: NodeJS.ProcessEnv,
  required: (name: string) => string,
  problems: string[],
  user: string,
  passwordVar: string,
): DatabaseConfig {
  const host = required('POSTGRES_HOST');
  const password = required(passwordVar);
  const database = env.POSTGRES_DB?.trim() || DATABASE_NAME;
  if (database !== DATABASE_NAME) {
    problems.push(`POSTGRES_DB must be "${DATABASE_NAME}" in every environment (got "${database}")`);
  }
  const port = parsePort('POSTGRES_PORT', env.POSTGRES_PORT, 5432, problems);
  return { host, port, database, user, password };
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
