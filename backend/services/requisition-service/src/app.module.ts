import { DynamicModule, Module } from '@nestjs/common';
import { PlatformModule, ServiceConfig } from '@teamora/platform';
import { JdVersionsModule } from './jd-versions/jd-versions.module';
import { RequisitionsModule } from './requisitions/requisitions.module';
import { ScoringMatrixModule } from './scoring-matrix/scoring-matrix.module';

@Module({})
export class AppModule {
  static register(config: ServiceConfig): DynamicModule {
    return {
      module: AppModule,
      imports: [PlatformModule.forRoot(config), RequisitionsModule, JdVersionsModule, ScoringMatrixModule],
    };
  }
}
