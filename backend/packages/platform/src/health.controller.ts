import { Controller, Get, Inject, ServiceUnavailableException } from '@nestjs/common';
import { ServiceConfig } from './config';
import { DB_POOL, SERVICE_CONFIG } from './tokens';

interface Queryable {
  query(sql: string): Promise<unknown>;
}

@Controller('health')
export class HealthController {
  constructor(
    @Inject(SERVICE_CONFIG) private readonly config: ServiceConfig,
    @Inject(DB_POOL) private readonly pool: Queryable,
  ) {}

  /** Liveness: the process is up. This is the Coolify health-check path (SOP §8.3). */
  @Get()
  live() {
    return { status: 'ok', service: this.config.serviceName, appEnv: this.config.appEnv };
  }

  /** Readiness: the service can reach its database as its own role. */
  @Get('ready')
  async ready() {
    try {
      await this.pool.query('SELECT 1');
    } catch {
      // No error detail in the response: it could reveal hosts or usernames.
      throw new ServiceUnavailableException({
        status: 'error',
        service: this.config.serviceName,
        checks: { database: 'down' },
      });
    }
    return { status: 'ok', service: this.config.serviceName, checks: { database: 'up' } };
  }
}
