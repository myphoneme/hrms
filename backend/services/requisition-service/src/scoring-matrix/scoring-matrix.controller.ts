import { Body, Controller, Delete, Get, HttpCode, HttpStatus, Param, Patch, Post, Query, UseGuards } from '@nestjs/common';
import { ApiBody, ApiOperation, ApiTags } from '@nestjs/swagger';
import { Auth, AuthContext, AuthGuard } from '@teamora/platform';
import { requireIdParam } from '../common/tenant-scope';
import { MatrixDto, ScoringMatrixService } from './scoring-matrix.service';
import { parseRevisionQuery, validateAddCriterion, validateEditWeights } from './scoring-matrix.validation';

/** Draft scoring matrix of one JD version — HR-M1-FR-006 (TDD §8). */
@ApiTags('HR-M1-FR-006 · Scoring matrix')
@Controller('requisitions/:requisitionId/jd-versions/:versionId/scoring-matrix/draft')
@UseGuards(AuthGuard)
export class DraftMatrixController {
  constructor(private readonly matrices: ScoringMatrixService) {}

  @ApiOperation({ summary: 'The draft matrix of a JD version (created empty on first read)' })
  @Get()
  get(@Param('requisitionId') r: string, @Param('versionId') v: string, @Auth() auth: AuthContext): Promise<MatrixDto> {
    return this.matrices.getDraft(auth, requireIdParam(r, 'requisition'), requireIdParam(v, 'version'));
  }

  /** `{ matrix_revision, criteria: [{ criterion_id, weight_percent }] }` → `{ status, matrix_revision, current_total_percent }`. */
  @ApiOperation({ summary: 'Adjust weights (total checked only at freeze); matrix_revision must be the one you last read' })
  @ApiBody({ schema: { type: 'object', example: { matrix_revision: 5, criteria: [{ criterion_id: '<criterion id from GET>', weight_percent: 40 }] } } })
  @Patch()
  editWeights(@Param('requisitionId') r: string, @Param('versionId') v: string, @Body() body: unknown, @Auth() auth: AuthContext) {
    return this.matrices.editWeights(auth, requireIdParam(r, 'requisition'), requireIdParam(v, 'version'), validateEditWeights(body));
  }

  /** `{ matrix_revision, category, criterion_name, weight_percent }` → the updated matrix. */
  @ApiOperation({ summary: 'Add a criterion (categories: core_skills, experience_seniority, domain_competency, education_fit)' })
  @ApiBody({ schema: { type: 'object', example: { matrix_revision: 1, category: 'core_skills', criterion_name: 'Power BI proficiency', weight_percent: 45 } } })
  @Post('criteria')
  @HttpCode(HttpStatus.CREATED)
  addCriterion(@Param('requisitionId') r: string, @Param('versionId') v: string, @Body() body: unknown, @Auth() auth: AuthContext) {
    return this.matrices.addCriterion(auth, requireIdParam(r, 'requisition'), requireIdParam(v, 'version'), validateAddCriterion(body));
  }

  /** `DELETE .../criteria/{criterionId}?matrix_revision=N` → the updated matrix. */
  @ApiOperation({ summary: 'Remove a criterion (?matrix_revision=N)' })
  @Delete('criteria/:criterionId')
  removeCriterion(
    @Param('requisitionId') r: string,
    @Param('versionId') v: string,
    @Param('criterionId') c: string,
    @Query('matrix_revision') revision: unknown,
    @Auth() auth: AuthContext,
  ): Promise<MatrixDto> {
    return this.matrices.removeCriterion(
      auth,
      requireIdParam(r, 'requisition'),
      requireIdParam(v, 'version'),
      requireIdParam(c, 'criterion'),
      parseRevisionQuery(revision),
    );
  }
}

/** GET /requisitions/{id}/scoring-matrix — the Approved matrix of the active version (TDD §8). */
@ApiTags('HR-M1-FR-006 · Scoring matrix')
@Controller('requisitions/:requisitionId/scoring-matrix')
@UseGuards(AuthGuard)
export class ApprovedMatrixController {
  constructor(private readonly matrices: ScoringMatrixService) {}

  @ApiOperation({ summary: 'The Approved matrix of the active version (after freeze)' })
  @Get()
  get(@Param('requisitionId') r: string, @Auth() auth: AuthContext): Promise<MatrixDto> {
    return this.matrices.getApproved(auth, requireIdParam(r, 'requisition'));
  }
}
