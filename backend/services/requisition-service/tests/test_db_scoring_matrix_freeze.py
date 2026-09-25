"""HR-M1-FR-006 — draft-then-freeze weighted scoring matrix (BRD §4.1, §5; TDD §6, §8, §12.1), plus the
HR-M1-FR-004 "repeat freeze is a no-op" scenario, against a real database."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import psycopg
import pytest

from teamora_common import TenantScope, with_tenant

pytestmark = pytest.mark.db

BALANCED = [
    ("core_skills", "Power BI proficiency", 45),
    ("experience_seniority", "5+ years analytics", 30),
    ("domain_competency", "Retail domain", 20),
    ("education_fit", "Graduate degree", 5),
]


@pytest.fixture(scope="module")
def tenant(id_pool, helpers):
    return helpers.create_tenant(id_pool, "direct_employer")


@pytest.fixture(scope="module")
def api(client, tenant, helpers):
    manager = helpers.manager_of(tenant)
    api = helpers.Api(client, manager)
    api.auth = manager
    return api


def ok(res, status=200):
    assert res.status_code == status, res.text
    return res.json()


def base(r):
    return f"/api/v1/requisitions/{r}"


def draft_url(r, v):
    return f"{base(r)}/jd-versions/{v}/scoring-matrix/draft"


@pytest.fixture
def new_requisition(client, api, helpers):
    return lambda: helpers.create_requisition(client, api.auth)


@pytest.fixture
def pending_version(api, new_requisition):
    """A requisition with one PendingApproval version whose draft matrix holds ``weights``."""

    def make(weights, requisition_id=None):
        r = requisition_id or new_requisition()
        v = ok(api.post(f"{base(r)}/jd-versions", {"content": f"JD for {r}"}), 201)["id"]
        revision = ok(api.get(draft_url(r, v)))["matrix_revision"]
        for category, name, weight in weights:
            body = {"matrix_revision": revision, "category": category, "criterion_name": name, "weight_percent": weight}
            revision = ok(api.post(f"{draft_url(r, v)}/criteria", body), 201)["matrix_revision"]
        ok(api.post(f"{base(r)}/jd-versions/{v}/submit"))
        return r, v, revision

    return make


def freeze(api, r, approved, expected):
    return api.post(f"{base(r)}/freeze", {"approved_version_id": approved, "expected_active_version_id": expected})


def state(req_pool, tenant, r):
    with with_tenant(req_pool, TenantScope(tenant)) as db:
        requisition = db.execute(
            "SELECT status, active_version_id FROM requisition.job_requisition WHERE id = %s", (r,)
        ).fetchone()
        versions = db.execute(
            "SELECT id, status, superseded_by FROM requisition.jd_version WHERE requisition_id = %s ORDER BY version_no", (r,)
        ).fetchall()
        matrices = db.execute(
            """SELECT m.jd_version_id, m.status FROM requisition.scoring_matrix m
                 JOIN requisition.jd_version v ON v.id = m.jd_version_id WHERE v.requisition_id = %s ORDER BY v.version_no""",
            (r,),
        ).fetchall()
    return {"requisition": requisition, "versions": versions, "matrices": matrices}


class TestDraftMatrix:
    def test_starts_empty_grows_by_criteria_and_tracks_the_total_and_revision(self, api, new_requisition):
        r = new_requisition()
        v = ok(api.post(f"{base(r)}/jd-versions", {"content": "JD"}), 201)["id"]
        empty = ok(api.get(draft_url(r, v)))
        assert (empty["status"], empty["matrix_revision"], empty["criteria"], empty["current_total_percent"]) == (
            "Draft",
            1,
            [],
            0,
        )

        body = {"matrix_revision": 1, "category": "core_skills", "criterion_name": "SQL", "weight_percent": 33.33}
        added = ok(api.post(f"{draft_url(r, v)}/criteria", body), 201)
        assert (added["matrix_revision"], added["current_total_percent"]) == (2, 33.33)
        c = added["criteria"][0]
        assert (c["category"], c["criterion_name"], c["weight_percent"]) == ("core_skills", "SQL", 33.33)

    def test_lets_the_manager_adjust_weights_and_saves_a_partial_draft(self, api, pending_version):
        r, v, revision = pending_version(BALANCED)
        core = next(c for c in ok(api.get(draft_url(r, v)))["criteria"] if c["category"] == "core_skills")
        body = {"matrix_revision": revision, "criteria": [{"criterion_id": core["criterion_id"], "weight_percent": 40}]}
        assert ok(api.patch(draft_url(r, v), body)) == {
            "status": "Draft",
            "matrix_revision": revision + 1,
            "current_total_percent": 95,
        }

    def test_rejects_an_edit_against_an_old_revision_and_returns_the_current_state(self, api, pending_version):
        r, v, revision = pending_version(BALANCED)
        criterion = ok(api.get(draft_url(r, v)))["criteria"][0]["criterion_id"]
        ok(
            api.patch(
                draft_url(r, v), {"matrix_revision": revision, "criteria": [{"criterion_id": criterion, "weight_percent": 10}]}
            )
        )
        stale = ok(
            api.patch(
                draft_url(r, v), {"matrix_revision": revision, "criteria": [{"criterion_id": criterion, "weight_percent": 20}]}
            ),
            409,
        )
        assert (stale["reason"], stale["current_matrix_revision"]) == ("revision_mismatch", revision + 1)
        assert next(c for c in stale["current_criteria"] if c["criterion_id"] == criterion)["weight_percent"] == 10

    def test_has_no_soft_skill_category_and_enforces_per_criterion_bounds(self, api, new_requisition):
        r = new_requisition()
        v = ok(api.post(f"{base(r)}/jd-versions", {"content": "JD"}), 201)["id"]
        ok(api.get(draft_url(r, v)))
        body = {"matrix_revision": 1, "category": "behavioral_proxy", "criterion_name": "Teamwork", "weight_percent": 101}
        res = ok(api.post(f"{draft_url(r, v)}/criteria", body), 422)
        assert [d["field"] for d in res["details"]] == ["category", "weight_percent"]


class TestFreeze:
    # BRD §4.1: manager submits matrix weights that sum to 100%.
    def test_approves_the_version_and_its_matrix_together_when_weights_total_100(self, api, pending_version, req_pool, tenant):
        r, v, _ = pending_version(BALANCED)
        res = ok(freeze(api, r, v, None))
        assert (res["status"], res["active_version_id"], res["superseded_version_id"]) == ("Frozen_Open", v, None)
        assert res["scoring_matrix_id"]
        s = state(req_pool, tenant, r)
        assert s["requisition"] == {"status": "Frozen_Open", "active_version_id": v}
        assert s["versions"] == [{"id": v, "status": "Approved", "superseded_by": None}]
        assert s["matrices"] == [{"jd_version_id": v, "status": "Approved"}]

        approved = ok(api.get(f"{base(r)}/scoring-matrix"))
        assert (approved["status"], approved["jd_version_id"], approved["current_total_percent"]) == ("Approved", v, 100)
        datetime.fromisoformat(approved["approved_at"])

    # BRD §4.1: manager submits matrix weights that do not sum to 100%.
    def test_rejects_a_freeze_whose_weights_do_not_total_100_changing_nothing(self, api, pending_version, req_pool, tenant):
        r, v, _ = pending_version([("core_skills", "SQL", 60), ("education_fit", "Degree", 30)])
        before = state(req_pool, tenant, r)
        res = ok(freeze(api, r, v, None), 409)
        assert (res["reason"], res["details"]) == ("matrix_total_invalid", {"current_total_percent": 90})
        assert state(req_pool, tenant, r) == before

    # BRD §4.1: two managers attempt to freeze the same requisition simultaneously.
    def test_lets_exactly_one_of_two_simultaneous_freezes_succeed(self, api, pending_version, req_pool, tenant):
        r, first, _ = pending_version(BALANCED)
        _, second, _ = pending_version(BALANCED, r)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda v: freeze(api, r, v, None), [first, second]))
        assert sorted(res.status_code for res in results) == [200, 409]
        winner = next(res.json() for res in results if res.status_code == 200)
        loser = next(res.json() for res in results if res.status_code == 409)
        assert (loser["reason"], loser["current_active_version_id"]) == ("stale_expected_version", winner["active_version_id"])
        assert len([v for v in state(req_pool, tenant, r)["versions"] if v["status"] == "Approved"]) == 1

    # BRD §4.1 (HR-M1-FR-004): manager repeats an identical freeze request already applied.
    def test_treats_an_exact_repeat_of_a_successful_freeze_as_a_no_op(self, api, pending_version, req_pool, tenant):
        r, v, _ = pending_version(BALANCED)
        first_call = ok(freeze(api, r, v, None))
        before = state(req_pool, tenant, r)
        assert ok(freeze(api, r, v, None)) == first_call
        assert state(req_pool, tenant, r) == before

    def test_supersedes_the_previously_approved_version_when_a_revision_is_frozen(self, api, pending_version, req_pool, tenant):
        r, v1, _ = pending_version(BALANCED)
        ok(freeze(api, r, v1, None))
        _, v2, _ = pending_version(BALANCED, r)
        res = ok(freeze(api, r, v2, v1))
        assert (res["active_version_id"], res["superseded_version_id"]) == (v2, v1)

        s = state(req_pool, tenant, r)
        assert s["versions"] == [
            {"id": v1, "status": "Superseded", "superseded_by": v2},
            {"id": v2, "status": "Approved", "superseded_by": None},
        ]
        # The superseded version keeps its own Approved matrix for assessments that used it (TDD §6).
        assert s["matrices"] == [{"jd_version_id": v1, "status": "Approved"}, {"jd_version_id": v2, "status": "Approved"}]
        assert ok(api.get(draft_url(r, v1)))["status"] == "Approved"

    def test_rejects_a_version_not_awaiting_approval_or_a_stale_expectation(self, api, new_requisition, pending_version):
        r = new_requisition()
        draft = ok(api.post(f"{base(r)}/jd-versions", {"content": "Not submitted"}), 201)["id"]
        not_ready = ok(freeze(api, r, draft, None), 409)
        assert (not_ready["reason"], not_ready["details"]) == ("version_not_approvable", {"current_status": "Draft"})

        _, version, _ = pending_version(BALANCED, r)
        assert ok(freeze(api, r, version, draft), 409)["reason"] == "stale_expected_version"

    def test_requires_expected_active_version_id_to_be_present(self, api, pending_version):
        r, v, _ = pending_version(BALANCED)
        res = ok(api.post(f"{base(r)}/freeze", {"approved_version_id": v}), 422)
        assert res["details"][0]["field"] == "expected_active_version_id"

    def test_makes_an_approved_matrix_immutable_through_the_api_and_in_the_database(self, api, pending_version, req_pool, tenant):
        r, v, revision = pending_version(BALANCED)
        ok(freeze(api, r, v, None))
        criterion = ok(api.get(draft_url(r, v)))["criteria"][0]["criterion_id"]
        edit = ok(
            api.patch(
                draft_url(r, v), {"matrix_revision": revision, "criteria": [{"criterion_id": criterion, "weight_percent": 1}]}
            ),
            409,
        )
        assert edit["reason"] == "matrix_approved"
        with pytest.raises(psycopg.Error) as exc, with_tenant(req_pool, TenantScope(tenant)) as db:
            db.execute("UPDATE requisition.scoring_criterion SET weight_percent = 1 WHERE id = %s", (criterion,))
        assert exc.value.sqlstate == "TM020"

    def test_never_approves_a_matrix_in_the_database_unless_it_totals_100_and_its_version_is_approved(
        self, pending_version, req_pool, tenant
    ):
        approve = "UPDATE requisition.scoring_matrix SET status = 'Approved', approved_at = now() WHERE jd_version_id = %s"
        _, partial, _ = pending_version([("core_skills", "SQL", 50)])
        with pytest.raises(psycopg.Error) as exc, with_tenant(req_pool, TenantScope(tenant)) as db:
            db.execute(approve, (partial,))
        assert exc.value.sqlstate == "TM021"
        _, complete, _ = pending_version(BALANCED)
        with pytest.raises(psycopg.Error) as exc, with_tenant(req_pool, TenantScope(tenant)) as db:
            db.execute(approve, (complete,))
        assert exc.value.sqlstate == "TM022"

    def test_never_lets_another_tenant_read_or_freeze_a_requisition(self, pending_version, client, id_pool, helpers):
        r, v, _ = pending_version(BALANCED)
        outsider = helpers.Api(client, helpers.manager_of(helpers.create_tenant(id_pool, "direct_employer")))
        assert freeze(outsider, r, v, None).status_code == 404
        assert outsider.get(draft_url(r, v)).status_code == 404
        assert outsider.get(f"{base(r)}/scoring-matrix").status_code == 404
