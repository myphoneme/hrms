"""HR-M1-FR-005 — pieces of the approval SLA that need no database."""

import time
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from requisition_service import SERVICE, build_app
from requisition_service.sla import PolicyRequest, add_business_days, interval_from_env
from teamora_common import AuthContext, ConfigError, DatabaseConfig, ServiceConfig, sign_access_token

IST = "Asia/Kolkata"


def ist(day: int, hour: int = 16) -> datetime:
    """A moment in September 2026, India time (2026-09-25 is a Friday)."""
    return datetime.fromisoformat(f"2026-09-{day:02d}T{hour:02d}:00:00+05:30")


@pytest.mark.parametrize(
    ("start", "days", "expected"),
    [
        (ist(21), 3, ist(24)),  # Monday + 3 -> Thursday
        (ist(25), 3, ist(30)),  # Friday + 3 -> Wednesday (weekend skipped)
        (ist(25), 1, ist(28)),  # Friday + 1 -> Monday
        (ist(26, 10), 1, ist(28, 10)),  # Saturday + 1 -> Monday, same time of day
        (ist(21), 5, ist(28)),  # Monday + 5 -> next Monday
    ],
)
def test_adds_business_days_in_the_tenants_time_zone(start, days, expected):
    assert add_business_days(start, days, IST) == expected


def test_business_days_follow_the_local_calendar_not_utc():
    # 22:00 UTC on Friday is already Saturday 03:30 in India: +1 business day lands on Monday 03:30 IST.
    friday_night_utc = datetime(2026, 9, 25, 22, 0, tzinfo=UTC)
    assert add_business_days(friday_night_utc, 1, IST) == datetime.fromisoformat("2026-09-28T03:30:00+05:30")


def test_policy_requires_escalation_after_reminder_and_a_real_time_zone():
    PolicyRequest(reminder_after_business_days=2, escalate_after_business_days=4, timezone="Europe/London")
    with pytest.raises(ValidationError, match="greater than reminder"):
        PolicyRequest(reminder_after_business_days=3, escalate_after_business_days=3)
    with pytest.raises(ValidationError, match="IANA time zone"):
        PolicyRequest(reminder_after_business_days=1, escalate_after_business_days=2, timezone="Mars/Olympus")
    with pytest.raises(ValidationError, match="from 1 to 20"):
        PolicyRequest(reminder_after_business_days=0, escalate_after_business_days=2)


def test_check_interval_comes_from_the_environment():
    assert interval_from_env({}) == 300
    assert interval_from_env({"SLA_CHECK_INTERVAL_SECONDS": "0"}) == 0
    assert interval_from_env({"SLA_CHECK_INTERVAL_SECONDS": "60"}) == 60
    with pytest.raises(ConfigError, match="SLA_CHECK_INTERVAL_SECONDS"):
        interval_from_env({"SLA_CHECK_INTERVAL_SECONDS": "soon"})


SECRET = "e2e-test-secret-e2e-test-secret-000001"
CONFIG = ServiceConfig(
    service_name=SERVICE.service_name,
    app_env="test",
    port=0,
    db=DatabaseConfig(host="unused", port=5432, database="teamora", user=SERVICE.db_role, password="unused"),
    auth_jwt_secret=SECRET,
)


class UnreachablePool:
    def connection(self):
        raise AssertionError("database must not be reached")


class CountingPool:
    """Answers the SLA check's first query with no due clocks, counting how often it's asked."""

    def __init__(self) -> None:
        self.checks = 0

    @contextmanager
    def connection(self):
        yield self

    def execute(self, sql, *_):
        if "approval_sla_clock" in sql:
            self.checks += 1
        return self

    def fetchall(self):
        return []


def test_the_background_check_runs_on_its_interval_and_stops_with_the_service():
    pool = CountingPool()
    with TestClient(build_app(CONFIG, pool=pool, sla_interval_seconds=0.05)):
        time.sleep(0.4)
        assert pool.checks >= 2
    stopped_at = pool.checks
    time.sleep(0.2)
    assert pool.checks == stopped_at


def test_only_a_tenant_admin_may_change_the_sla_policy():
    secret = SECRET
    config = CONFIG
    manager = AuthContext(
        user_id="0190a1b2-0000-7000-8000-000000000001", tenant_id="0190a1b2-0000-7000-8000-00000000000a", role="manager"
    )
    with TestClient(build_app(config, pool=UnreachablePool())) as client:
        res = client.put(
            "/api/v1/sla-policy",
            json={"reminder_after_business_days": 2, "escalate_after_business_days": 4},
            headers={"Authorization": f"Bearer {sign_access_token(secret, manager)}"},
        )
    assert res.status_code == 403
    assert res.json()["reason"] == "role_not_allowed"
