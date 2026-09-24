import { Body, Controller, HttpCode, HttpStatus, Param, Post, UseGuards } from '@nestjs/common';
import { Auth, AuthContext, AuthGuard } from '@teamora/platform';
import { requireIdParam } from '../common/tenant-scope';
import { FreezeResult, FreezeService, validateFreeze } from './freeze.service';

/** POST /requisitions/{id}/freeze — HR-M1-FR-006 (TDD §8). */
@Controller('requisitions/:requisitionId/freeze')
@UseGuards(AuthGuard)
export class FreezeController {
  constructor(private readonly freezes: FreezeService) {}

  /** `{ approved_version_id, expected_active_version_id }` → `{ status, active_version_id, scoring_matrix_id, superseded_version_id }`. */
  @Post()
  @HttpCode(HttpStatus.OK)
  freeze(@Param('requisitionId') r: string, @Body() body: unknown, @Auth() auth: AuthContext): Promise<FreezeResult> {
    return this.freezes.freeze(auth, requireIdParam(r, 'requisition'), validateFreeze(body));
  }
}
