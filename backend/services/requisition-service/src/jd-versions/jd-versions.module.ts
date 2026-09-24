import { Module } from '@nestjs/common';
import { JdVersionsController } from './jd-versions.controller';
import { JdVersionsService } from './jd-versions.service';

@Module({
  controllers: [JdVersionsController],
  providers: [JdVersionsService],
})
export class JdVersionsModule {}
