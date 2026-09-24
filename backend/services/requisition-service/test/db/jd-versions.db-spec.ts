// HR-M1-FR-004 — JD versioning & audit trail (BRD §4.1; TDD §6.0, §6, §15), against a real database.
import { INestApplication } from '@nestjs/common';
import { AuthContext, withTenant } from '@teamora/platform';
import { Pool } from 'pg';
import { api, createRequisition, createTenant, identityPool, managerOf, requisitionPool, startApp } from './helpers';

describe('HR-M1-FR-004 — JD versioning & audit trail', () => {
  let app: INestApplication;
  let idPool: Pool;
  let reqPool: Pool;
  let tenant: string;
  let manager: AuthContext;

  beforeAll(async () => {
    idPool = identityPool();
    reqPool = requisitionPool();
    tenant = await createTenant(idPool, 'direct_employer');
    manager = managerOf(tenant);
    app = await startApp();
  });

  afterAll(async () => {
    await app.close();
    await idPool.end();
    await reqPool.end();
  });

  const versionsUrl = (requisitionId: string) => `/api/v1/requisitions/${requisitionId}/jd-versions`;

  /** Simulates the freeze (HR-M1-FR-006): PendingApproval -> Approved and point the requisition at it. */
  const approveDirectly = (requisitionId: string, versionId: string) =>
    withTenant(reqPool, { tenantId: tenant, clientId: null }, async (db) => {
      await db.query("UPDATE requisition.jd_version SET status = 'Approved' WHERE id = $1", [versionId]);
      await db.query("UPDATE requisition.job_requisition SET active_version_id = $2, status = 'Frozen_Open' WHERE id = $1", [
        requisitionId,
        versionId,
      ]);
    });

  it('stores every edit as a new version with author and timestamp, numbered in order', async () => {
    const requisitionId = await createRequisition(app, manager);
    const v1 = await api(app, manager).post(versionsUrl(requisitionId), { content: 'First draft', variant_type: 'formal' }).expect(201);
    const v2 = await api(app, manager)
      .post(versionsUrl(requisitionId), { content: 'Second draft', based_on_version_id: v1.body.id })
      .expect(201);

    expect(v1.body).toMatchObject({ version_no: 1, status: 'Draft', variant_type: 'formal', generated_by: 'manager', created_by: manager.userId });
    expect(v2.body).toMatchObject({ version_no: 2, status: 'Revising', variant_type: 'manager_edited', based_on_version_id: v1.body.id });
    expect(Date.parse(v2.body.created_at)).not.toBeNaN();

    const history = await api(app, manager).get(versionsUrl(requisitionId)).expect(200);
    expect(history.body.map((v: { version_no: number; content: string }) => [v.version_no, v.content])).toEqual([
      [1, 'First draft'],
      [2, 'Second draft'],
    ]);
  });

  it('moves a requisition and its version through submit for approval', async () => {
    const requisitionId = await createRequisition(app, manager);
    const v1 = await api(app, manager).post(versionsUrl(requisitionId), { content: 'Draft' }).expect(201);
    const submitted = await api(app, manager).post(`${versionsUrl(requisitionId)}/${v1.body.id}/submit`).expect(200);
    expect(submitted.body.status).toBe('PendingApproval');
    expect(await requisitionStatus(requisitionId)).toBe('PendingApproval');

    // Submitting again is not a valid transition.
    const again = await api(app, manager).post(`${versionsUrl(requisitionId)}/${v1.body.id}/submit`).expect(409);
    expect(again.body).toMatchObject({ reason: 'version_not_submittable', details: { current_status: 'PendingApproval' } });

    // Manager requests changes: a revision puts the requisition back into Revising (TDD §6.0).
    await api(app, manager).post(versionsUrl(requisitionId), { content: 'Revised', based_on_version_id: v1.body.id }).expect(201);
    expect(await requisitionStatus(requisitionId)).toBe('Revising');
  });

  // BRD §4.1 acceptance scenario: manager edits a JD after it has already been Approved (frozen).
  it('rejects a direct edit of an Approved version; the edit opens a new version instead', async () => {
    const requisitionId = await createRequisition(app, manager);
    const v1 = await api(app, manager).post(versionsUrl(requisitionId), { content: 'Approved text' }).expect(201);
    await api(app, manager).post(`${versionsUrl(requisitionId)}/${v1.body.id}/submit`).expect(200);
    await approveDirectly(requisitionId, v1.body.id);

    const edit = await api(app, manager).patch(`${versionsUrl(requisitionId)}/${v1.body.id}`, { content: 'Changed' }).expect(409);
    expect(edit.body).toMatchObject({ reason: 'version_immutable', details: { based_on_version_id: v1.body.id } });

    const revision = await api(app, manager)
      .post(versionsUrl(requisitionId), { content: 'Changed', based_on_version_id: v1.body.id })
      .expect(201);
    expect(revision.body).toMatchObject({ version_no: 2, status: 'Revising' });

    const history = await api(app, manager).get(versionsUrl(requisitionId)).expect(200);
    expect(history.body[0]).toMatchObject({ id: v1.body.id, status: 'Approved', content: 'Approved text' });
    // A frozen requisition stays Frozen_Open while a later revision is under review (TDD §6.0).
    expect(await requisitionStatus(requisitionId)).toBe('Frozen_Open');
  });

  describe('database guarantees (hold even without the API)', () => {
    let requisitionId: string;
    let approvedId: string;

    beforeAll(async () => {
      requisitionId = await createRequisition(app, manager);
      const v1 = await api(app, manager).post(versionsUrl(requisitionId), { content: 'Frozen JD' }).expect(201);
      await api(app, manager).post(`${versionsUrl(requisitionId)}/${v1.body.id}/submit`).expect(200);
      await approveDirectly(requisitionId, v1.body.id);
      approvedId = v1.body.id;
    });

    const sql = (text: string, params: unknown[]) =>
      withTenant(reqPool, { tenantId: tenant, clientId: null }, (db) => db.query(text, params));

    it('never changes version content, whatever the status (TM010)', async () => {
      await expect(sql("UPDATE requisition.jd_version SET content = 'tampered' WHERE id = $1", [approvedId])).rejects.toMatchObject({
        code: 'TM010',
      });
    });

    it('never deletes a version', async () => {
      await expect(sql('DELETE FROM requisition.jd_version WHERE id = $1', [approvedId])).rejects.toThrow(/permission denied/);
    });

    it('allows only the TDD §6.0 status transitions (TM012)', async () => {
      await expect(sql("UPDATE requisition.jd_version SET status = 'Draft' WHERE id = $1", [approvedId])).rejects.toMatchObject({
        code: 'TM012',
      });
      const v2 = await api(app, manager).post(versionsUrl(requisitionId), { content: 'Next' }).expect(201);
      // Draft cannot jump straight to Approved: it must go through PendingApproval (freeze).
      await expect(sql("UPDATE requisition.jd_version SET status = 'Approved' WHERE id = $1", [v2.body.id])).rejects.toMatchObject({
        code: 'TM012',
      });
    });

    it('never inserts a version directly as Approved', async () => {
      await expect(
        sql(
          `INSERT INTO requisition.jd_version (requisition_id, version_no, variant_type, content, generated_by, status, created_by)
           VALUES ($1, 99, 'formal', 'x', 'manager', 'Approved', $2)`,
          [requisitionId, manager.userId],
        ),
      ).rejects.toMatchObject({ code: 'TM012' });
    });

    it('allows at most one Approved version per requisition', async () => {
      const v3 = await api(app, manager).post(versionsUrl(requisitionId), { content: 'Another' }).expect(201);
      await api(app, manager).post(`${versionsUrl(requisitionId)}/${v3.body.id}/submit`).expect(200);
      await expect(sql("UPDATE requisition.jd_version SET status = 'Approved' WHERE id = $1", [v3.body.id])).rejects.toMatchObject({
        code: '23505',
      });
    });

    it('supersedes an Approved version only by pointing at its replacement', async () => {
      await expect(sql("UPDATE requisition.jd_version SET status = 'Superseded' WHERE id = $1", [approvedId])).rejects.toMatchObject({
        code: '23514',
      });
    });
  });

  it("rejects a based_on_version_id from another requisition (422)", async () => {
    const reqA = await createRequisition(app, manager);
    const reqB = await createRequisition(app, manager);
    const vA = await api(app, manager).post(versionsUrl(reqA), { content: 'A' }).expect(201);
    const res = await api(app, manager).post(versionsUrl(reqB), { content: 'B', based_on_version_id: vA.body.id }).expect(422);
    expect(res.body.reason).toBe('unknown_base_version');
  });

  it("does not show or accept versions on another tenant's requisition (404)", async () => {
    const requisitionId = await createRequisition(app, manager);
    await api(app, manager).post(versionsUrl(requisitionId), { content: 'Private' }).expect(201);
    const outsider = managerOf(await createTenant(idPool, 'direct_employer'));
    expect((await api(app, outsider).get(versionsUrl(requisitionId)).expect(404)).body.reason).toBe('requisition_not_found');
    await api(app, outsider).post(versionsUrl(requisitionId), { content: 'Sneaky' }).expect(404);
  });

  it('refuses JD changes on a Closed requisition (409)', async () => {
    const requisitionId = await createRequisition(app, manager);
    await withTenant(reqPool, { tenantId: tenant, clientId: null }, (db) =>
      db.query("UPDATE requisition.job_requisition SET status = 'Closed' WHERE id = $1", [requisitionId]),
    );
    const res = await api(app, manager).post(versionsUrl(requisitionId), { content: 'Late' }).expect(409);
    expect(res.body.reason).toBe('requisition_not_editable');
  });

  it('returns 404 for a malformed id and 422 for an invalid body', async () => {
    await api(app, manager).get(versionsUrl('not-a-uuid')).expect(404);
    const requisitionId = await createRequisition(app, manager);
    const res = await api(app, manager).post(versionsUrl(requisitionId), { content: ' ', variant_type: 'poem' }).expect(422);
    expect(res.body.details.map((d: { field: string }) => d.field)).toEqual(['content', 'variant_type']);
  });

  async function requisitionStatus(requisitionId: string): Promise<string> {
    return withTenant(reqPool, { tenantId: tenant, clientId: null }, async (db) => {
      const { rows } = await db.query<{ status: string }>('SELECT status FROM requisition.job_requisition WHERE id = $1', [requisitionId]);
      return rows[0].status;
    });
  }
});
