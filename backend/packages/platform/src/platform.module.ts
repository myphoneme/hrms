import { DynamicModule, Inject, Injectable, Module, OnApplicationShutdown } from '@nestjs/common';
import { ServiceConfig } from './config';
import { createPool } from './db';
import { HealthController } from './health.controller';
import { DB_POOL, SERVICE_CONFIG } from './tokens';

@Injectable()
class PoolShutdown implements OnApplicationShutdown {
  constructor(@Inject(DB_POOL) private readonly pool: { end?: () => Promise<void> }) {}

  async onApplicationShutdown(): Promise<void> {
    if (typeof this.pool.end === 'function') await this.pool.end();
  }
}

/**
 * Foundation every Teamora NestJS service imports once, in its root module:
 * provides SERVICE_CONFIG and DB_POOL to the whole app and serves GET /health and GET /health/ready.
 */
@Module({})
export class PlatformModule {
  static forRoot(config: ServiceConfig): DynamicModule {
    return {
      module: PlatformModule,
      global: true,
      controllers: [HealthController],
      providers: [
        { provide: SERVICE_CONFIG, useValue: config },
        { provide: DB_POOL, useFactory: () => createPool(config) },
        PoolShutdown,
      ],
      exports: [SERVICE_CONFIG, DB_POOL],
    };
  }
}
