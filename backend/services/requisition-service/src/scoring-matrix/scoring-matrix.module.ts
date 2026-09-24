import { Module } from '@nestjs/common';
import { FreezeController } from '../freeze/freeze.controller';
import { FreezeService } from '../freeze/freeze.service';
import { ApprovedMatrixController, DraftMatrixController } from './scoring-matrix.controller';
import { ScoringMatrixService } from './scoring-matrix.service';

@Module({
  controllers: [DraftMatrixController, ApprovedMatrixController, FreezeController],
  providers: [ScoringMatrixService, FreezeService],
})
export class ScoringMatrixModule {}
