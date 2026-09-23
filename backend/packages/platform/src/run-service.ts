import 'reflect-metadata';
import { DynamicModule, INestApplication, Logger } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { ConfigError, loadServiceConfig, ServiceConfig, ServiceDefinition } from './config';

/** App-wide settings shared by every service; also applied in tests so they match production. */
export function configureApp(app: INestApplication): INestApplication {
  // Business APIs live under /api/v1 (Readiness doc §2.3); health endpoints stay at the root for Coolify.
  app.setGlobalPrefix('api/v1', { exclude: ['health', 'health/ready'] });
  app.enableShutdownHooks();
  return app;
}

/**
 * Entry point for a service's main.ts: loads and validates configuration, starts the app,
 * and logs APP_ENV and the database target at startup (Charter v1.1, Database rules 7).
 */
export async function runService(
  def: ServiceDefinition,
  buildModule: (config: ServiceConfig) => DynamicModule,
): Promise<void> {
  const logger = new Logger(def.serviceName);
  let config: ServiceConfig;
  try {
    config = loadServiceConfig(def);
  } catch (err) {
    if (err instanceof ConfigError) {
      logger.error(err.message);
      process.exit(1);
    }
    throw err;
  }

  const app = configureApp(await NestFactory.create(buildModule(config)));
  await app.listen(config.port, '0.0.0.0');
  const { db } = config;
  logger.log(
    `listening on :${config.port} | APP_ENV=${config.appEnv} | DB=${db.user}@${db.host}:${db.port}/${db.database}`,
  );
}
