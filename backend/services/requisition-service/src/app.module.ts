import { DynamicModule, Module } from '@nestjs/common';
import { PlatformModule, ServiceConfig } from '@teamora/platform';
import { RequisitionsModule } from './requisitions/requisitions.module';

@Module({})
export class AppModule {
  static register(config: ServiceConfig): DynamicModule {
    return {
      module: AppModule,
      imports: [PlatformModule.forRoot(config), RequisitionsModule],
    };
  }
}
