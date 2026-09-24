import { Body, ConflictException, Controller, Get, HttpCode, HttpStatus, Param, Patch, Post, UseGuards } from '@nestjs/common';
import { Auth, AuthContext, AuthGuard } from '@teamora/platform';
import { requireIdParam } from '../common/tenant-scope';
import { JdVersionDto, JdVersionsService } from './jd-versions.service';
import { validateCreateVersion } from './jd-versions.validation';

/** JD versions of a requisition — HR-M1-FR-004 (TDD §6, §8). */
@Controller('requisitions/:requisitionId/jd-versions')
@UseGuards(AuthGuard)
export class JdVersionsController {
  constructor(private readonly versions: JdVersionsService) {}

  /** GET — the full version history, including Approved/Superseded/Rejected versions. */
  @Get()
  list(@Param('requisitionId') requisitionId: string, @Auth() auth: AuthContext): Promise<JdVersionDto[]> {
    return this.versions.list(auth, requireIdParam(requisitionId, 'requisition'));
  }

  /** POST — every edit is a new version: `{ content, variant_type?, based_on_version_id? }`. */
  @Post()
  @HttpCode(HttpStatus.CREATED)
  create(
    @Param('requisitionId') requisitionId: string,
    @Body() body: unknown,
    @Auth() auth: AuthContext,
  ): Promise<JdVersionDto> {
    return this.versions.create(auth, requireIdParam(requisitionId, 'requisition'), validateCreateVersion(body));
  }

  /** POST .../{versionId}/submit — send a Draft/Revising version for approval. */
  @Post(':versionId/submit')
  @HttpCode(HttpStatus.OK)
  submit(
    @Param('requisitionId') requisitionId: string,
    @Param('versionId') versionId: string,
    @Auth() auth: AuthContext,
  ): Promise<JdVersionDto> {
    return this.versions.submit(auth, requireIdParam(requisitionId, 'requisition'), requireIdParam(versionId, 'version'));
  }

  /**
   * PATCH — versions are never edited in place (HR-M1-FR-004; TDD §15 "Manager attempts to edit a
   * frozen JD"): always 409, pointing to the correct path, a new version based on this one.
   */
  @Patch(':versionId')
  edit(@Param('requisitionId') requisitionId: string, @Param('versionId') versionId: string): never {
    throw new ConflictException({
      reason: 'version_immutable',
      message: 'JD versions are never edited in place. Create a new version based on this one instead.',
      details: {
        create_new_version: `POST /api/v1/requisitions/${requisitionId}/jd-versions`,
        based_on_version_id: versionId,
      },
    });
  }
}
