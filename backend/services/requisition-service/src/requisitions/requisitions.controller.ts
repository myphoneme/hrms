import { Body, Controller, HttpCode, HttpStatus, Post, UseGuards } from '@nestjs/common';
import { ApiBody, ApiOperation, ApiTags } from '@nestjs/swagger';
import { Auth, AuthContext, AuthGuard } from '@teamora/platform';
import { validateIntake } from './intake.validation';
import { IntakeResult, RequisitionsService } from './requisitions.service';

@ApiTags('HR-M1-FR-007 · Requisition intake')
@Controller('requisitions')
@UseGuards(AuthGuard)
export class RequisitionsController {
  constructor(private readonly requisitions: RequisitionsService) {}

  /**
   * POST /api/v1/requisitions/intake — creates a requisition from a manager's raw brief (TDD §8).
   * HR-M1-FR-007: an agency tenant must name its end-client; a direct employer must send client_id: null.
   */
  @ApiOperation({ summary: 'Create a Draft requisition from a raw brief (agency: client required; direct employer: client_id null)' })
  @ApiBody({
    schema: {
      type: 'object',
      example: { tenant_id: '11111111-1111-4111-8111-111111111111', client_id: '22222222-2222-4222-8222-222222222222', department_id: null, raw_brief_text: 'Need a senior data analyst: Power BI, SQL, 5+ years, retail domain.', source: 'portal' },
    },
  })
  @Post('intake')
  @HttpCode(HttpStatus.CREATED)
  intake(@Body() body: unknown, @Auth() auth: AuthContext): Promise<IntakeResult> {
    return this.requisitions.createFromIntake(validateIntake(body, auth));
  }
}
