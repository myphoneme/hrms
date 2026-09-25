"""HR-M1-FR-005 — approval SLA & escalation (BRD §4.1; TDD §12.1 step 7, §14), against a real database."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import pytest

from requisition_service.sla import run_sla_check
from teamora_common import AuthContext, TenantScope, with_tenant

pytestmark = pytest.mark.db

MINUTE = timedelta(minutes=1)


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


@pytest.fixture
def pending(client, api, helpers):
    """A requisition whose first JD version was just sent to the manager (PendingApproval)."""

    def make(auth_api=None):
        a = auth_api or api
        r = helpers.create_requisition(client, a.auth)
        v = ok(a.post(f"/api/v1/requisitions/{r}/jd-versions", {"content": "JD"}), 201)["id"]
        ok(a.post(f"/api/v1/requisitions/{r}/jd-versions/{v}/submit"))
        return r, v

    return make


def sla(api, r):
    return ok(api.get(f"/api/v1/requisitions/{r}/sla"))


def at(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def check(client, now):
    return run_sla_check(client.app.state.pool, now=now)


def events_of(api, r):
    return sla(api, r)["events"]


# BRD §4.1 acceptance scenario: manager does not respond within the configured SLA window.
def test_reminder_then_hr_escalation_fire_from_the_scheduled_check(client, api, pending):
    r, v = pending()
    state = sla(api, r)
    clock = state["clock"]
    assert (clock["status"], clock["jd_version_id"], state["policy"]["is_default"]) == ("open", v, True)
    reminder_due, escalation_due = at(clock["reminder_due_at"]), at(clock["escalation_due_at"])
    assert reminder_due < escalation_due

    check(client, reminder_due - MINUTE)
    assert events_of(api, r) == []

    check(client, reminder_due + MINUTE)
    [reminder] = events_of(api, r)
    assert (reminder["kind"], reminder["recipient_role"], reminder["recipient_user_id"]) == (
        "reminder",
        "manager",
        api.auth.user_id,
    )
    assert (reminder["delivery_status"], at(reminder["due_at"])) == ("pending", reminder_due)

    check(client, reminder_due + 2 * MINUTE)  # a later check doesn't repeat it
    assert len(events_of(api, r)) == 1

    check(client, escalation_due + MINUTE)
    kinds = [(e["kind"], e["recipient_role"], e["recipient_user_id"]) for e in events_of(api, r)]
    assert kinds == [("reminder", "manager", api.auth.user_id), ("escalation", "recruiter_hr", None)]
    clock = sla(api, r)["clock"]
    assert clock["reminded_at"] and clock["escalated_at"] and clock["status"] == "open"


def test_both_fire_if_the_check_was_down_past_both_thresholds(client, api, pending):
    r, _ = pending()
    escalation_due = at(sla(api, r)["clock"]["escalation_due_at"])
    summary = check(client, escalation_due + MINUTE)
    assert summary["reminders"] >= 1 and summary["escalations"] >= 1
    assert [e["kind"] for e in events_of(api, r)] == ["reminder", "escalation"]


@pytest.mark.parametrize("how", ["revision", "freeze", "close"])
def test_a_manager_response_stops_the_clock(client, api, pending, req_pool, tenant, how):
    r, v = pending()
    reminder_due = at(sla(api, r)["clock"]["reminder_due_at"])
    base = f"/api/v1/requisitions/{r}"
    if how == "revision":  # manager asks for changes: a new version based on the pending one
        ok(api.post(f"{base}/jd-versions", {"content": "Changed", "based_on_version_id": v}), 201)
        expected = "revised"
    elif how == "freeze":
        revision = ok(api.get(f"{base}/jd-versions/{v}/scoring-matrix/draft"))["matrix_revision"]
        body = {"matrix_revision": revision, "category": "core_skills", "criterion_name": "SQL", "weight_percent": 100}
        ok(api.post(f"{base}/jd-versions/{v}/scoring-matrix/draft/criteria", body), 201)
        ok(api.post(f"{base}/freeze", {"approved_version_id": v, "expected_active_version_id": None}))
        expected = "Approved"
    else:  # requisition closed
        with with_tenant(req_pool, TenantScope(tenant)) as db:
            db.execute("UPDATE requisition.job_requisition SET status = 'Closed' WHERE id = %s", (r,))
        expected = "Closed"

    clock = sla(api, r)["clock"]
    assert (clock["status"], clock["resolution"]) == ("resolved", expected)
    check(client, reminder_due + timedelta(days=30))
    assert events_of(api, r) == []


def test_resubmitting_after_a_revision_starts_a_new_clock(client, api, pending):
    r, v1 = pending()
    base = f"/api/v1/requisitions/{r}/jd-versions"
    v2 = ok(api.post(base, {"content": "Revised", "based_on_version_id": v1}), 201)["id"]
    ok(api.post(f"{base}/{v2}/submit"))
    clock = sla(api, r)["clock"]
    assert (clock["status"], clock["jd_version_id"]) == ("open", v2)


def test_the_tenant_admin_sets_the_thresholds(client, id_pool, helpers, pending):
    tenant = helpers.create_tenant(id_pool, "direct_employer")
    admin = helpers.Api(client, AuthContext(user_id=helpers.manager_of(tenant).user_id, tenant_id=tenant, role="tenant_admin"))
    manager_auth = helpers.manager_of(tenant)
    manager = helpers.Api(client, manager_auth)
    manager.auth = manager_auth

    assert ok(admin.get("/api/v1/sla-policy"))["is_default"] is True
    body = {"reminder_after_business_days": 1, "escalate_after_business_days": 2, "timezone": "Asia/Kolkata"}
    saved = ok(admin.client.put("/api/v1/sla-policy", json=body, headers=admin.headers))
    assert (saved["reminder_after_business_days"], saved["escalate_after_business_days"], saved["is_default"]) == (1, 2, False)

    assert ok(manager.client.put("/api/v1/sla-policy", json=body, headers=manager.headers), 403)["reason"] == "role_not_allowed"
    bad = {"reminder_after_business_days": 3, "escalate_after_business_days": 3}
    assert ok(admin.client.put("/api/v1/sla-policy", json=bad, headers=admin.headers), 422)["reason"] == "validation_failed"

    # The new thresholds apply: reminder 1 business day after sending, escalation 2.
    r, _ = pending(manager)
    clock = sla(manager, r)["clock"]
    since = at(clock["pending_since"])
    assert timedelta(days=1) <= at(clock["reminder_due_at"]) - since <= timedelta(days=3)
    assert at(clock["escalation_due_at"]) > at(clock["reminder_due_at"])


def test_other_tenants_never_see_the_sla_or_events(client, api, pending, id_pool, helpers):
    r, _ = pending()
    check(client, at(sla(api, r)["clock"]["escalation_due_at"]) + MINUTE)
    outsider_tenant = helpers.create_tenant(id_pool, "direct_employer")
    hr = helpers.Api(
        client, AuthContext(user_id=helpers.manager_of(outsider_tenant).user_id, tenant_id=outsider_tenant, role="recruiter_hr")
    )
    assert hr.get(f"/api/v1/requisitions/{r}/sla").status_code == 404
    assert all(e["requisition_id"] != r for e in ok(hr.get("/api/v1/sla-events")))


def test_hr_sees_escalations_and_a_manager_only_their_own_reminders(client, api, pending, tenant, helpers):
    r, _ = pending()
    check(client, at(sla(api, r)["clock"]["escalation_due_at"]) + MINUTE)
    hr = helpers.Api(client, AuthContext(user_id=helpers.manager_of(tenant).user_id, tenant_id=tenant, role="recruiter_hr"))
    escalations = ok(hr.get("/api/v1/sla-events?kind=escalation"))
    assert any(e["requisition_id"] == r for e in escalations)
    assert all(e["kind"] == "escalation" for e in escalations)

    mine = ok(api.get("/api/v1/sla-events"))
    assert mine and all(e["recipient_user_id"] == api.auth.user_id for e in mine)
    other_manager = helpers.Api(client, helpers.manager_of(tenant))
    assert all(e["requisition_id"] != r for e in ok(other_manager.get("/api/v1/sla-events")))


def test_two_checks_at_once_record_each_reminder_only_once(client, api, pending):
    r, _ = pending()
    reminder_due = at(sla(api, r)["clock"]["reminder_due_at"])
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: check(client, reminder_due + MINUTE), range(2)))
    assert [e["kind"] for e in events_of(api, r)] == ["reminder"]
