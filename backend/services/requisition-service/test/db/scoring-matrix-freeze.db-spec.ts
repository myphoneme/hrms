// HR-M1-FR-006 — draft-then-freeze weighted scoring matrix (BRD §4.1, §5; TDD §6, §8, §12.1), plus the
// HR-M1-FR-004 "repeat freeze is a no-op" scenario, against a real database.
import { INestApplication } from '@nestjs/common';
import { AuthContext, withTenant } from '@teamora/platform';
import { Pool } from 'pg';
import { api, createRequisition, createTenant, identityPool, managerOf, requisitionPool, startApp } from './helpers';

type Weights = Array<[category: string, name: string, weight: number]>;
const BALANCED: Weights = [
  ['core_skills', 'Power BI proficiency', 45],
  ['experience_seniority', '5+ years analytics', 30],
  ['domain_competency', 'Retail domain', 20],
  ['education_fit', 'Graduate degree', 5],
];

describe('HR-M1-FR-006 — draft-then-freeze weighted scoring matrix', () => {
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

  const base = (r: string) => `/api/v1/requisitions/${r}`;
  const draftUrl = (r: string, v: string) => `${base(r)}/jd-versions/${v}/scoring-matrix/draft`;

  /** A requisition with one PendingApproval version whose draft matrix holds `weights`. */
  async function pendingVersion(weights: Weights, requisitionId?: string): Promise<{ requisitionId: string; versionId: string; revision: number }> {
    const r = requisitionId ?? (await createRequisition(app, manager));
    const v = await api(app, manager).post(`${base(r)}/jd-versions`, { content: `JD for ${r}` }).expect(201);
    let revision = (await api(app, manager).get(draftUrl(r, v.body.id)).expect(200)).body.matrix_revision;
    for (const [category, criterion_name, weight_percent] of weights) {
      const res = await api(app, manager)
        .post(`${draftUrl(r, v.body.id)}/criteria`, { matrix_revision: revision, category, criterion_name, weight_percent })
        .expect(201);
      revision = res.body.matrix_revision;
    }
    await api(app, manager).post(`${base(r)}/jd-versions/${v.body.id}/submit`).expect(200);
    return { requisitionId: r, versionId: v.body.id, revision };
  }

  const freeze = (r: string, approved: string, expected: string | null) =>
    api(app, manager).post(`${base(r)}/freeze`, { approved_version_id: approved, expected_active_version_id: expected });

  const state = (r: string) =>
    withTenant(reqPool, { tenantId: tenant, clientId: null }, async (db) => {
      const req = await db.query('SELECT status, active_version_id FROM requisition.job_requisition WHERE id = $1', [r]);
      const versions = await db.query('SELECT id, status, superseded_by FROM requisition.jd_version WHERE requisition_id = $1 ORDER BY version_no', [r]);
      const matrices = await db.query(
        `SELECT m.jd_version_id, m.status FROM requisition.scoring_matrix m
           JOIN requisition.jd_version v ON v.id = m.jd_version_id WHERE v.requisition_id = $1 ORDER BY v.version_no`,
        [r],
      );
      return { requisition: req.rows[0], versions: versions.rows, matrices: matrices.rows };
    });

  describe('draft matrix', () => {
    it('starts empty, grows by criteria and tracks the running total and revision', async () => {
      const r = await createRequisition(app, manager);
      const v = await api(app, manager).post(`${base(r)}/jd-versions`, { content: 'JD' }).expect(201);
      const empty = await api(app, manager).get(draftUrl(r, v.body.id)).expect(200);
      expect(empty.body).toMatchObject({ status: 'Draft', matrix_revision: 1, criteria: [], current_total_percent: 0 });

      const added = await api(app, manager)
        .post(`${draftUrl(r, v.body.id)}/criteria`, { matrix_revision: 1, category: 'core_skills', criterion_name: 'SQL', weight_percent: 33.33 })
        .expect(201);
      expect(added.body).toMatchObject({ matrix_revision: 2, current_total_percent: 33.33 });
      expect(added.body.criteria[0]).toMatchObject({ category: 'core_skills', criterion_name: 'SQL', weight_percent: 33.33 });
    });

    it('lets the manager adjust weights and saves a partial (non-100) draft', async () => {
      const { requisitionId: r, versionId: v, revision } = await pendingVersion(BALANCED);
      const draft = await api(app, manager).get(draftUrl(r, v)).expect(200);
      const core = draft.body.criteria.find((c: { category: string }) => c.category === 'core_skills');
      const res = await api(app, manager)
        .patch(draftUrl(r, v), { matrix_revision: revision, criteria: [{ criterion_id: core.criterion_id, weight_percent: 40 }] })
        .expect(200);
      expect(res.body).toEqual({ status: 'Draft', matrix_revision: revision + 1, current_total_percent: 95 });
    });

    it('rejects an edit made against an old revision and returns the current state (two tabs)', async () => {
      const { requisitionId: r, versionId: v, revision } = await pendingVersion(BALANCED);
      const draft = await api(app, manager).get(draftUrl(r, v)).expect(200);
      const id = draft.body.criteria[0].criterion_id;
      await api(app, manager).patch(draftUrl(r, v), { matrix_revision: revision, criteria: [{ criterion_id: id, weight_percent: 10 }] }).expect(200);
      const stale = await api(app, manager)
        .patch(draftUrl(r, v), { matrix_revision: revision, criteria: [{ criterion_id: id, weight_percent: 20 }] })
        .expect(409);
      expect(stale.body).toMatchObject({ reason: 'revision_mismatch', current_matrix_revision: revision + 1 });
      expect(stale.body.current_criteria.find((c: { criterion_id: string }) => c.criterion_id === id).weight_percent).toBe(10);
    });

    it('has no soft-skill / behavioral category and enforces per-criterion bounds (422)', async () => {
      const r = await createRequisition(app, manager);
      const v = await api(app, manager).post(`${base(r)}/jd-versions`, { content: 'JD' }).expect(201);
      await api(app, manager).get(draftUrl(r, v.body.id)).expect(200);
      const res = await api(app, manager)
        .post(`${draftUrl(r, v.body.id)}/criteria`, { matrix_revision: 1, category: 'behavioral_proxy', criterion_name: 'Teamwork', weight_percent: 101 })
        .expect(422);
      expect(res.body.details.map((d: { field: string }) => d.field)).toEqual(['category', 'weight_percent']);
    });
  });

  describe('freeze', () => {
    // BRD §4.1: manager submits matrix weights that sum to 100%.
    it('approves the JD version and its matrix together when weights total 100%', async () => {
      const { requisitionId: r, versionId: v } = await pendingVersion(BALANCED);
      const res = await freeze(r, v, null).expect(200);
      expect(res.body).toEqual({
        status: 'Frozen_Open',
        active_version_id: v,
        scoring_matrix_id: expect.any(String),
        superseded_version_id: null,
      });
      const s = await state(r);
      expect(s.requisition).toEqual({ status: 'Frozen_Open', active_version_id: v });
      expect(s.versions).toEqual([{ id: v, status: 'Approved', superseded_by: null }]);
      expect(s.matrices).toEqual([{ jd_version_id: v, status: 'Approved' }]);

      const approved = await api(app, manager).get(`${base(r)}/scoring-matrix`).expect(200);
      expect(approved.body).toMatchObject({ status: 'Approved', jd_version_id: v, current_total_percent: 100 });
      expect(Date.parse(approved.body.approved_at)).not.toBeNaN();
    });

    // BRD §4.1: manager submits matrix weights that do not sum to 100%.
    it('rejects a freeze whose weights do not total 100% with the offending total, changing nothing', async () => {
      const { requisitionId: r, versionId: v } = await pendingVersion([['core_skills', 'SQL', 60], ['education_fit', 'Degree', 30]]);
      const before = await state(r);
      const res = await freeze(r, v, null).expect(409);
      expect(res.body).toMatchObject({ reason: 'matrix_total_invalid', details: { current_total_percent: 90 } });
      expect(await state(r)).toEqual(before);
    });

    // BRD §4.1: two managers attempt to freeze the same requisition simultaneously.
    it('lets exactly one of two simultaneous freezes succeed; the other gets 409 against the new state', async () => {
      const first = await pendingVersion(BALANCED);
      const second = await pendingVersion(BALANCED, first.requisitionId);
      const results = await Promise.all([
        freeze(first.requisitionId, first.versionId, null),
        freeze(first.requisitionId, second.versionId, null),
      ]);
      const statuses = results.map((r) => r.status).sort();
      expect(statuses).toEqual([200, 409]);
      const loser = results.find((r) => r.status === 409)!;
      const winner = results.find((r) => r.status === 200)!;
      expect(loser.body).toMatchObject({ reason: 'stale_expected_version', current_active_version_id: winner.body.active_version_id });
      const approved = (await state(first.requisitionId)).versions.filter((v: { status: string }) => v.status === 'Approved');
      expect(approved).toHaveLength(1);
    });

    // BRD §4.1 (HR-M1-FR-004): manager repeats an identical freeze request already applied.
    it('treats an exact repeat of a successful freeze as a no-op with the same response', async () => {
      const { requisitionId: r, versionId: v } = await pendingVersion(BALANCED);
      const firstCall = await freeze(r, v, null).expect(200);
      const before = await state(r);
      const repeat = await freeze(r, v, null).expect(200);
      expect(repeat.body).toEqual(firstCall.body);
      expect(await state(r)).toEqual(before);
    });

    it('supersedes the previously approved version (kept, never overwritten) when a revision is frozen', async () => {
      const { requisitionId: r, versionId: v1 } = await pendingVersion(BALANCED);
      await freeze(r, v1, null).expect(200);
      const { versionId: v2 } = await pendingVersion(BALANCED, r);
      const res = await freeze(r, v2, v1).expect(200);
      expect(res.body).toMatchObject({ active_version_id: v2, superseded_version_id: v1 });

      const s = await state(r);
      expect(s.versions).toEqual([
        { id: v1, status: 'Superseded', superseded_by: v2 },
        { id: v2, status: 'Approved', superseded_by: null },
      ]);
      // The superseded version keeps its own Approved matrix for assessments that used it (TDD §6).
      expect(s.matrices).toEqual([
        { jd_version_id: v1, status: 'Approved' },
        { jd_version_id: v2, status: 'Approved' },
      ]);
      expect((await api(app, manager).get(draftUrl(r, v1)).expect(200)).body.status).toBe('Approved');
    });

    it('rejects freezing a version that is not awaiting approval, or with a stale expectation', async () => {
      const r = await createRequisition(app, manager);
      const draft = await api(app, manager).post(`${base(r)}/jd-versions`, { content: 'Not submitted' }).expect(201);
      const notReady = await freeze(r, draft.body.id, null).expect(409);
      expect(notReady.body).toMatchObject({ reason: 'version_not_approvable', details: { current_status: 'Draft' } });

      const { versionId } = await pendingVersion(BALANCED, r);
      const stale = await freeze(r, versionId, draft.body.id).expect(409);
      expect(stale.body.reason).toBe('stale_expected_version');
    });

    it('requires expected_active_version_id to be present (null is valid) — 422', async () => {
      const { requisitionId: r, versionId: v } = await pendingVersion(BALANCED);
      const res = await api(app, manager).post(`${base(r)}/freeze`, { approved_version_id: v }).expect(422);
      expect(res.body.details[0].field).toBe('expected_active_version_id');
    });

    it('makes an Approved matrix immutable, through the API and in the database', async () => {
      const { requisitionId: r, versionId: v, revision } = await pendingVersion(BALANCED);
      await freeze(r, v, null).expect(200);
      const matrix = (await api(app, manager).get(draftUrl(r, v)).expect(200)).body;
      const edit = await api(app, manager)
        .patch(draftUrl(r, v), { matrix_revision: revision, criteria: [{ criterion_id: matrix.criteria[0].criterion_id, weight_percent: 1 }] })
        .expect(409);
      expect(edit.body.reason).toBe('matrix_approved');
      await expect(
        withTenant(reqPool, { tenantId: tenant, clientId: null }, (db) =>
          db.query('UPDATE requisition.scoring_criterion SET weight_percent = 1 WHERE id = $1', [matrix.criteria[0].criterion_id]),
        ),
      ).rejects.toMatchObject({ code: 'TM020' });
    });

    it('never approves a matrix in the database unless it totals 100 and its version is Approved', async () => {
      const { versionId: v } = await pendingVersion([['core_skills', 'SQL', 50]]);
      await expect(
        withTenant(reqPool, { tenantId: tenant, clientId: null }, (db) =>
          db.query("UPDATE requisition.scoring_matrix SET status = 'Approved', approved_at = now() WHERE jd_version_id = $1", [v]),
        ),
      ).rejects.toMatchObject({ code: 'TM021' });
      const ok = await pendingVersion(BALANCED);
      await expect(
        withTenant(reqPool, { tenantId: tenant, clientId: null }, (db) =>
          db.query("UPDATE requisition.scoring_matrix SET status = 'Approved', approved_at = now() WHERE jd_version_id = $1", [ok.versionId]),
        ),
      ).rejects.toMatchObject({ code: 'TM022' });
    });

    it("never lets another tenant read or freeze a requisition (404)", async () => {
      const { requisitionId: r, versionId: v } = await pendingVersion(BALANCED);
      const outsider = managerOf(await createTenant(idPool, 'direct_employer'));
      await api(app, outsider).post(`${base(r)}/freeze`, { approved_version_id: v, expected_active_version_id: null }).expect(404);
      await api(app, outsider).get(draftUrl(r, v)).expect(404);
      await api(app, outsider).get(`${base(r)}/scoring-matrix`).expect(404);
    });
  });
});
