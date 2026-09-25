"""Shared setup for requisition-service database tests (``pytest -m db``).

They run against a real, bootstrapped and migrated ``teamora`` database. The API runs as
svc_requisition; test tenants are seeded as svc_auth. Required env: POSTGRES_HOST, POSTGRES_PORT,
POSTGRES_SVC_AUTH_PASSWORD, POSTGRES_SVC_REQUISITION_PASSWORD.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from requisition_service import SERVICE, build_app
from teamora_common import AuthContext, DatabaseConfig, ServiceConfig, TenantScope, create_pool, sign_access_token, with_tenant

SECRET = "db-test-secret-db-test-secret-0000001"


def _config(service_name: str, user: str, password_var: str) -> ServiceConfig:
    return ServiceConfig(
        service_name=service_name,
        app_env="test",
        port=0,
        db=DatabaseConfig(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            database="teamora",
            user=user,
            password=os.environ.get(password_var, ""),
        ),
        auth_jwt_secret=SECRET,
    )


def _open(config: ServiceConfig) -> Iterator[ConnectionPool]:
    pool = create_pool(config)
    pool.open(wait=True)
    try:
        yield pool
    finally:
        pool.close()


@pytest.fixture(scope="module")
def id_pool() -> Iterator[ConnectionPool]:
    """Logged in as svc_auth: seeds tenants and clients in the identity schema."""
    yield from _open(_config("tests:identity", "svc_auth", "POSTGRES_SVC_AUTH_PASSWORD"))


@pytest.fixture(scope="module")
def req_pool() -> Iterator[ConnectionPool]:
    """Logged in as svc_requisition: direct SQL checks against the requisition schema."""
    yield from _open(_config("tests:requisition", "svc_requisition", "POSTGRES_SVC_REQUISITION_PASSWORD"))


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    """The real app with its real pool (svc_requisition)."""
    config = _config(SERVICE.service_name, SERVICE.db_role, SERVICE.db_password_var)
    with TestClient(build_app(config)) as c:
        yield c


def create_tenant(id_pool: ConnectionPool, org_type: str) -> str:
    tenant_id = str(uuid.uuid4())
    with with_tenant(id_pool, TenantScope(tenant_id)) as db:
        db.execute(
            "INSERT INTO identity.tenant (id, org_type, name) VALUES (%s, %s, %s)",
            (tenant_id, org_type, f"{org_type} {tenant_id}"),
        )
    return tenant_id


def create_client(id_pool: ConnectionPool, tenant_id: str) -> str:
    with with_tenant(id_pool, TenantScope(tenant_id)) as db:
        return db.execute(
            "INSERT INTO identity.client (agency_tenant_id, name) VALUES (%s, 'End client') RETURNING id", (tenant_id,)
        ).fetchone()["id"]


def manager_of(tenant_id: str) -> AuthContext:
    return AuthContext(user_id=str(uuid.uuid4()), tenant_id=tenant_id, role="manager")


class Api:
    """An authenticated caller of the app."""

    def __init__(self, client: TestClient, auth: AuthContext) -> None:
        self.client = client
        self.headers = {"Authorization": f"Bearer {sign_access_token(SECRET, auth)}"}

    def get(self, url: str):
        return self.client.get(url, headers=self.headers)

    def post(self, url: str, body: dict | None = None):
        return self.client.post(url, json=body or {}, headers=self.headers)

    def patch(self, url: str, body: dict | None = None):
        return self.client.patch(url, json=body or {}, headers=self.headers)


def create_requisition(client: TestClient, auth: AuthContext) -> str:
    """A direct-employer requisition created through the intake API."""
    res = Api(client, auth).post(
        "/api/v1/requisitions/intake",
        {"tenant_id": auth.tenant_id, "client_id": None, "raw_brief_text": "Data analyst, Power BI", "source": "portal"},
    )
    assert res.status_code == 201, res.text
    return res.json()["requisition_id"]


@pytest.fixture(scope="module")
def helpers():
    """Plain helper functions for test modules (importlib mode can't import a shared helpers module)."""

    class Helpers:
        Api = Api
        create_tenant = staticmethod(create_tenant)
        create_client = staticmethod(create_client)
        manager_of = staticmethod(manager_of)
        create_requisition = staticmethod(create_requisition)

    return Helpers
