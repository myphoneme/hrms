"""API-layer checks for POST /api/v1/requisitions/intake that must reject before touching the database.

The org_type rule itself (HR-M1-FR-007) is enforced by the database; see test_db_intake.py.
"""

import pytest
from fastapi.testclient import TestClient

from requisition_service import SERVICE, build_app
from teamora_common import AuthContext, DatabaseConfig, ServiceConfig, sign_access_token

SECRET = "e2e-test-secret-e2e-test-secret-000001"
CONFIG = ServiceConfig(
    service_name=SERVICE.service_name,
    app_env="test",
    port=0,
    db=DatabaseConfig(host="unused", port=5432, database="teamora", user=SERVICE.db_role, password="unused"),
    auth_jwt_secret=SECRET,
)
TENANT = "0190a1b2-0000-7000-8000-00000000000a"
MANAGER = AuthContext(user_id="0190a1b2-0000-7000-8000-000000000001", tenant_id=TENANT, role="manager")
VALID = {"tenant_id": TENANT, "client_id": None, "raw_brief_text": "Need a data analyst", "source": "portal"}


class UnreachablePool:
    def connection(self):
        raise AssertionError("database must not be reached")


@pytest.fixture(scope="module")
def client():
    with TestClient(build_app(CONFIG, pool=UnreachablePool())) as c:
        yield c


def post(client, body, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post("/api/v1/requisitions/intake", json=body, headers=headers)


def test_401_without_a_token(client):
    res = post(client, VALID)
    assert res.status_code == 401
    assert res.json()["reason"] == "missing_token"


def test_401_with_a_token_signed_by_another_key(client):
    res = post(client, VALID, sign_access_token("some-other-secret-some-other-secret-01", MANAGER))
    assert res.status_code == 401
    assert res.json()["reason"] == "invalid_token"


def test_403_when_tenant_id_is_not_the_callers_tenant(client):
    res = post(client, {**VALID, "tenant_id": "0190a1b2-0000-7000-8000-00000000000b"}, sign_access_token(SECRET, MANAGER))
    assert res.status_code == 403
    assert res.json()["reason"] == "tenant_mismatch"


def test_403_for_a_platform_admin_without_tenant_scope(client):
    admin = AuthContext(user_id=MANAGER.user_id, tenant_id=None, role="platform_admin")
    res = post(client, VALID, sign_access_token(SECRET, admin))
    assert res.status_code == 403
    assert res.json()["reason"] == "tenant_scope_required"


def test_422_when_client_id_is_omitted_even_though_null_is_valid(client):
    body = {k: v for k, v in VALID.items() if k != "client_id"}
    res = post(client, body, sign_access_token(SECRET, MANAGER))
    assert res.status_code == 422
    assert res.json() == {
        "reason": "validation_failed",
        "message": "The request body is invalid.",
        "details": [{"field": "client_id", "problem": "is required (use null for a direct-employer tenant)"}],
    }


def test_422_lists_every_invalid_field_at_once(client):
    res = post(
        client,
        {"tenant_id": "nope", "client_id": "also-nope", "raw_brief_text": "  ", "source": "fax"},
        sign_access_token(SECRET, MANAGER),
    )
    assert res.status_code == 422
    assert [d["field"] for d in res.json()["details"]] == ["tenant_id", "client_id", "raw_brief_text", "source"]


def test_422_for_a_body_that_is_not_an_object(client):
    res = post(client, [VALID], sign_access_token(SECRET, MANAGER))
    assert res.status_code == 422
    assert res.json()["details"] == [{"field": "(body)", "problem": "must be a JSON object"}]


def test_404_for_a_malformed_requisition_id(client):
    res = client.get(
        "/api/v1/requisitions/not-a-uuid/jd-versions", headers={"Authorization": f"Bearer {sign_access_token(SECRET, MANAGER)}"}
    )
    assert res.status_code == 404
    assert res.json()["reason"] == "requisition_not_found"
