import { Logger } from '@nestjs/common';
import { Pool } from 'pg';
import { ServiceConfig } from './config';

/**
 * One pool per service, logged in as the service's own role (e.g. svc_auth), which can only reach
 * its own schema. Never the superuser or teamora_migrator.
 */
export function createPool(config: ServiceConfig): Pool {
  const pool = new Pool({
    host: config.db.host,
    port: config.db.port,
    database: config.db.database,
    user: config.db.user,
    password: config.db.password,
    application_name: config.serviceName,
    max: 10,
    connectionTimeoutMillis: 5_000,
    idleTimeoutMillis: 30_000,
  });
  // An idle client losing its connection must not crash the process; the next query reconnects.
  const logger = new Logger('DatabasePool');
  pool.on('error', (err) => logger.error(`idle client error: ${err.message}`));
  return pool;
}
