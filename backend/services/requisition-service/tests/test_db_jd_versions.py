"""HR-M1-FR-004 — JD versioning & audit trail (BRD §4.1; TDD §6.0, §6, §15), against a real database."""

from datetime import datetime

import psycopg
import pytest

from teamora_common import TenantScope, with_tenant

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def tenant(id_pool, helpers):
    return helpers.create_tenant(id_pool, "direct_employer")


@pytest.fixture(scope="module")
def api(client, tenant, helpers):
    manager = helpers.manager_of(tenant)
    api = helpers.Api(client, manager)
    api.auth = manager
    return api


@pytest.fixture
def new_requisition(client, api, helpers):
    return lambda: helpers.create_requisition(client, api.auth)


def versions_url(requisition_id: str) -> str:
    return f"/api/v1/requisitions/{requisition_id}/jd-versions"


def ok(res, status=201):
    assert res.status_code == status, res.text
    return res.json()


def sql(req_pool, tenant, text, params):
    with with_tenant(req_pool, TenantScope(tenant)) as db:
        return db.execute(text, params)


def approve_directly(req_pool, tenant, requisition_id, version_id):
    """Simulates the freeze (HR-M1-FR-006): PendingApproval -> Approved and point the requisition at it."""
    with with_tenant(req_pool, TenantScope(tenant)) as db:
        db.execute("UPDATE requisition.jd_version SET status = 'Approved' WHERE id = %s", (version_id,))
        db.execute(
            "UPDATE requisition.job_requisition SET active_version_id = %s, status = 'Frozen_Open' WHERE id = %s",
            (version_id, requisition_id),
        )


def requisition_status(req_pool, tenant, requisition_id):
    with with_tenant(req_pool, TenantScope(tenant)) as db:
        return db.execute("SELECT status FROM requisition.job_requisition WHERE id = %s", (requisition_id,)).fetchone()["status"]


def test_stores_every_edit_as_a_new_version_with_author_and_timestamp(api, new_requisition):
    r = new_requisition()
    v1 = ok(api.post(versions_url(r), {"content": "First draft", "variant_type": "formal"}))
    v2 = ok(api.post(versions_url(r), {"content": "Second draft", "based_on_version_id": v1["id"]}))

    assert (v1["version_no"], v1["status"], v1["variant_type"], v1["generated_by"], v1["created_by"]) == (
        1, "Draft", "formal", "manager", api.auth.user_id,
    )  # fmt: skip
    assert (v2["version_no"], v2["status"], v2["variant_type"], v2["based_on_version_id"]) == (
        2, "Revising", "manager_edited", v1["id"],
    )  # fmt: skip
    datetime.fromisoformat(v2["created_at"])

    history = ok(api.get(versions_url(r)), 200)
    assert [(v["version_no"], v["content"]) for v in history] == [(1, "First draft"), (2, "Second draft")]


def test_moves_a_requisition_and_its_version_through_submit_for_approval(api, new_requisition, req_pool, tenant):
    r = new_requisition()
    v1 = ok(api.post(versions_url(r), {"content": "Draft"}))
    assert ok(api.post(f"{versions_url(r)}/{v1['id']}/submit"), 200)["status"] == "PendingApproval"
    assert requisition_status(req_pool, tenant, r) == "PendingApproval"

    # Submitting again is not a valid transition.
    again = ok(api.post(f"{versions_url(r)}/{v1['id']}/submit"), 409)
    assert (again["reason"], again["details"]) == ("version_not_submittable", {"current_status": "PendingApproval"})

    # Manager requests changes: a revision puts the requisition back into Revising (TDD §6.0).
    ok(api.post(versions_url(r), {"content": "Revised", "based_on_version_id": v1["id"]}))
    assert requisition_status(req_pool, tenant, r) == "Revising"


# BRD §4.1 acceptance scenario: manager edits a JD after it has already been Approved (frozen).
def test_rejects_a_direct_edit_of_an_approved_version_and_opens_a_new_version_instead(api, new_requisition, req_pool, tenant):
    r = new_requisition()
    v1 = ok(api.post(versions_url(r), {"content": "Approved text"}))
    ok(api.post(f"{versions_url(r)}/{v1['id']}/submit"), 200)
    approve_directly(req_pool, tenant, r, v1["id"])

    edit = ok(api.patch(f"{versions_url(r)}/{v1['id']}", {"content": "Changed"}), 409)
    assert edit["reason"] == "version_immutable"
    assert edit["details"]["based_on_version_id"] == v1["id"]

    revision = ok(api.post(versions_url(r), {"content": "Changed", "based_on_version_id": v1["id"]}))
    assert (revision["version_no"], revision["status"]) == (2, "Revising")

    first = ok(api.get(versions_url(r)), 200)[0]
    assert (first["id"], first["status"], first["content"]) == (v1["id"], "Approved", "Approved text")
    # A frozen requisition stays Frozen_Open while a later revision is under review (TDD §6.0).
    assert requisition_status(req_pool, tenant, r) == "Frozen_Open"


@pytest.fixture(scope="module")
def frozen(api, client, helpers, req_pool, tenant):
    """A requisition whose first version is Approved: (requisition_id, version_id)."""
    r = helpers.create_requisition(client, api.auth)
    v1 = ok(api.post(versions_url(r), {"content": "Frozen JD"}))
    ok(api.post(f"{versions_url(r)}/{v1['id']}/submit"), 200)
    approve_directly(req_pool, tenant, r, v1["id"])
    return r, v1["id"]


class TestDatabaseGuarantees:
    """These hold even without the API."""

    @staticmethod
    def rejected(req_pool, tenant, text, params) -> psycopg.Error:
        with pytest.raises(psycopg.Error) as exc:
            sql(req_pool, tenant, text, params)
        return exc.value

    def test_never_changes_version_content(self, frozen, req_pool, tenant):
        err = self.rejected(
            req_pool, tenant, "UPDATE requisition.jd_version SET content = 'tampered' WHERE id = %s", (frozen[1],)
        )
        assert err.sqlstate == "TM010"

    def test_never_deletes_a_version(self, frozen, req_pool, tenant):
        err = self.rejected(req_pool, tenant, "DELETE FROM requisition.jd_version WHERE id = %s", (frozen[1],))
        assert "permission denied" in str(err)

    def test_allows_only_the_tdd_status_transitions(self, frozen, api, req_pool, tenant):
        err = self.rejected(req_pool, tenant, "UPDATE requisition.jd_version SET status = 'Draft' WHERE id = %s", (frozen[1],))
        assert err.sqlstate == "TM012"
        v2 = ok(api.post(versions_url(frozen[0]), {"content": "Next"}))
        # Draft cannot jump straight to Approved: it must go through PendingApproval (freeze).
        err = self.rejected(req_pool, tenant, "UPDATE requisition.jd_version SET status = 'Approved' WHERE id = %s", (v2["id"],))
        assert err.sqlstate == "TM012"

    def test_never_inserts_a_version_directly_as_approved(self, frozen, api, req_pool, tenant):
        err = self.rejected(
            req_pool,
            tenant,
            """INSERT INTO requisition.jd_version (requisition_id, version_no, variant_type, content, generated_by, status, created_by)
               VALUES (%s, 99, 'formal', 'x', 'manager', 'Approved', %s)""",
            (frozen[0], api.auth.user_id),
        )
        assert err.sqlstate == "TM012"

    def test_allows_at_most_one_approved_version_per_requisition(self, frozen, api, req_pool, tenant):
        v3 = ok(api.post(versions_url(frozen[0]), {"content": "Another"}))
        ok(api.post(f"{versions_url(frozen[0])}/{v3['id']}/submit"), 200)
        err = self.rejected(req_pool, tenant, "UPDATE requisition.jd_version SET status = 'Approved' WHERE id = %s", (v3["id"],))
        assert err.sqlstate == "23505"

    def test_supersedes_an_approved_version_only_by_pointing_at_its_replacement(self, frozen, req_pool, tenant):
        err = self.rejected(
            req_pool, tenant, "UPDATE requisition.jd_version SET status = 'Superseded' WHERE id = %s", (frozen[1],)
        )
        assert err.sqlstate == "23514"


def test_rejects_a_base_version_from_another_requisition(api, new_requisition):
    req_a, req_b = new_requisition(), new_requisition()
    v_a = ok(api.post(versions_url(req_a), {"content": "A"}))
    res = ok(api.post(versions_url(req_b), {"content": "B", "based_on_version_id": v_a["id"]}), 422)
    assert res["reason"] == "unknown_base_version"


def test_does_not_show_or_accept_versions_on_another_tenants_requisition(api, new_requisition, client, id_pool, helpers):
    r = new_requisition()
    ok(api.post(versions_url(r), {"content": "Private"}))
    outsider = helpers.Api(client, helpers.manager_of(helpers.create_tenant(id_pool, "direct_employer")))
    assert ok(outsider.get(versions_url(r)), 404)["reason"] == "requisition_not_found"
    assert outsider.post(versions_url(r), {"content": "Sneaky"}).status_code == 404


def test_refuses_jd_changes_on_a_closed_requisition(api, new_requisition, req_pool, tenant):
    r = new_requisition()
    sql(req_pool, tenant, "UPDATE requisition.job_requisition SET status = 'Closed' WHERE id = %s", (r,))
    assert ok(api.post(versions_url(r), {"content": "Late"}), 409)["reason"] == "requisition_not_editable"


def test_returns_404_for_a_malformed_id_and_422_for_an_invalid_body(api, new_requisition):
    assert api.get(versions_url("not-a-uuid")).status_code == 404
    res = ok(api.post(versions_url(new_requisition()), {"content": " ", "variant_type": "poem"}), 422)
    assert [d["field"] for d in res["details"]] == ["content", "variant_type"]
