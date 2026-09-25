import { Body, Controller, HttpCode, HttpStatus, Param, Post, UseGuards } from '@nestjs/common';
import { ApiBody, ApiOperation, ApiTags } from '@nestjs/swagger';
import { Auth, AuthContext, AuthGuard } from '@teamora/platform';
import { requireIdParam } from '../common/tenant-scope';
import { FreezeResult, FreezeService, validateFreeze } from './freeze.service';

/** POST /requisitions/{id}/freeze — HR-M1-FR-006 (TDD §8). */
@ApiTags('HR-M1-FR-006 · Scoring matrix')
@Controller('requisitions/:requisitionId/freeze')
@UseGuards(AuthGuard)
export class FreezeController {
  constructor(private readonly freezes: FreezeService) {}

  /** `{ approved_version_id, expected_active_version_id }` → `{ status, active_version_id, scoring_matrix_id, superseded_version_id }`. */
  @ApiOperation({ summary: 'Freeze: approve a PendingApproval version + its matrix (weights must total 100%)' })
  @ApiBody({ schema: { type: 'object', example: { approved_version_id: '<PendingApproval version id>', expected_active_version_id: null } } })
  @Post()
  @HttpCode(HttpStatus.OK)
  freeze(@Param('requisitionId') r: string, @Body() body: unknown, @Auth() auth: AuthContext): Promise<FreezeResult> {
    return this.freezes.freeze(auth, requireIdParam(r, 'requisition'), validateFreeze(body));
  }
}
