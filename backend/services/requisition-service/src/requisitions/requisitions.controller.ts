import { Body, Controller, HttpCode, HttpStatus, Post, UseGuards } from '@nestjs/common';
import { Auth, AuthContext, AuthGuard } from '@teamora/platform';
import { validateIntake } from './intake.validation';
import { IntakeResult, RequisitionsService } from './requisitions.service';

@Controller('requisitions')
@UseGuards(AuthGuard)
export class RequisitionsController {
  constructor(private readonly requisitions: RequisitionsService) {}

  /**
   * POST /api/v1/requisitions/intake — creates a requisition from a manager's raw brief (TDD §8).
   * HR-M1-FR-007: an agency tenant must name its end-client; a direct employer must send client_id: null.
   */
  @Post('intake')
  @HttpCode(HttpStatus.CREATED)
  intake(@Body() body: unknown, @Auth() auth: AuthContext): Promise<IntakeResult> {
    return this.requisitions.createFromIntake(validateIntake(body, auth));
  }
}
