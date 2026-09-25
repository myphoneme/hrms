from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from auth_service import SERVICE, build_app
from teamora_common import DatabaseConfig, ServiceConfig

CONFIG = ServiceConfig(
    service_name=SERVICE.service_name,
    app_env="test",
    port=0,
    db=DatabaseConfig(host="unused", port=5432, database="teamora", user=SERVICE.db_role, password="unused"),
    auth_jwt_secret="e2e-test-secret-e2e-test-secret-000001",
)


class FakePool:
    """Stands in for the connection pool; records queries and can simulate a database outage."""

    def __init__(self) -> None:
        self.queries: list[str] = []
        self.down = False

    @contextmanager
    def connection(self):
        if self.down:
            raise ConnectionError("connect ECONNREFUSED 10.0.0.1:5432 user svc_auth")
        yield self

    def execute(self, sql, *_):
        self.queries.append(sql)


@pytest.fixture
def pool():
    return FakePool()


@pytest.fixture
def client(pool):
    with TestClient(build_app(CONFIG, pool=pool)) as c:
        yield c


def test_health_returns_200_without_touching_the_database(client, pool):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "auth-service", "appEnv": "test"}
    assert pool.queries == []


def test_ready_returns_200_when_the_database_answers(client):
    res = client.get("/health/ready")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "auth-service", "checks": {"database": "up"}}


def test_ready_returns_503_without_error_details_when_the_database_is_down(client, pool):
    pool.down = True
    res = client.get("/health/ready")
    assert res.status_code == 503
    assert res.json() == {"status": "error", "service": "auth-service", "checks": {"database": "down"}}
    assert "ECONNREFUSED" not in res.text


def test_health_stays_outside_the_api_prefix(client):
    assert client.get("/api/v1/health").status_code == 404


def test_unknown_route_returns_the_standard_error_body(client):
    res = client.get("/api/v1/does-not-exist")
    assert res.status_code == 404
    assert res.json() == {"reason": "not_found", "message": "Not Found"}


def test_api_docs_page_is_served_in_test_but_not_on_staging(pool):
    with TestClient(build_app(CONFIG, pool=pool)) as c:
        assert c.get("/api/docs").status_code == 200
    staging = ServiceConfig(**{**CONFIG.__dict__, "app_env": "staging"})
    with TestClient(build_app(staging, pool=pool)) as c:
        assert c.get("/api/docs").status_code == 404
        assert c.get("/api/openapi.json").status_code == 404
