"""identity schema: tenant isolation (TDD §5.3, BRD §5), against a real database, logged in as svc_auth.

Required env: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_SVC_AUTH_PASSWORD.
"""

import os
import uuid

import psycopg
import pytest

from teamora_common import DatabaseConfig, ServiceConfig, TenantScope, create_pool, with_tenant

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def pool():
    config = ServiceConfig(
        service_name="tests:identity",
        app_env="test",
        port=0,
        db=DatabaseConfig(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            database="teamora",
            user="svc_auth",
            password=os.environ.get("POSTGRES_SVC_AUTH_PASSWORD", ""),
        ),
        auth_jwt_secret="unused-unused-unused-unused-unused-00",
    )
    pool = create_pool(config)
    pool.open(wait=True)
    yield pool
    pool.close()


def create_tenant(pool, org_type, name):
    tenant_id = str(uuid.uuid4())
    with with_tenant(pool, TenantScope(tenant_id)) as db:
        db.execute("INSERT INTO identity.tenant (id, org_type, name) VALUES (%s, %s, %s)", (tenant_id, org_type, name))
    return tenant_id


def create_client(pool, tenant_id, name):
    with with_tenant(pool, TenantScope(tenant_id)) as db:
        return db.execute(
            "INSERT INTO identity.client (agency_tenant_id, name) VALUES (%s, %s) RETURNING id", (tenant_id, name)
        ).fetchone()["id"]


def create_user(pool, tenant_id, email):
    with with_tenant(pool, TenantScope(tenant_id)) as db:
        db.execute(
            "INSERT INTO identity.app_user (tenant_id, email, auth_method, role) VALUES (%s, %s, 'sso_google', 'manager')",
            (tenant_id, email),
        )


def count_visible(pool, tenant_id, table):
    with with_tenant(pool, TenantScope(tenant_id)) as db:
        return db.execute(f"SELECT count(*)::int AS n FROM identity.{table}").fetchone()["n"]


@pytest.fixture(scope="module")
def tenants(pool):
    agency_a = create_tenant(pool, "staffing_agency", "Agency A")
    agency_b = create_tenant(pool, "staffing_agency", "Agency B")
    employer = create_tenant(pool, "direct_employer", "Direct Employer")
    create_client(pool, agency_a, "Client of A")
    create_client(pool, agency_b, "Client of B")
    create_user(pool, agency_a, "manager@agency-a.test")
    create_user(pool, agency_b, "manager@agency-b.test")
    return {"a": agency_a, "b": agency_b, "employer": employer}


def rejected(fn) -> psycopg.Error:
    with pytest.raises(psycopg.Error) as exc:
        fn()
    return exc.value


def test_shows_nothing_without_a_tenant_scope(pool, tenants):
    with pool.connection() as db:
        for table in ("tenant", "client", "app_user"):
            assert db.execute(f"SELECT count(*)::int AS n FROM identity.{table}").fetchone()["n"] == 0


def test_shows_a_tenant_only_its_own_tenant_row_clients_and_users(pool, tenants):
    assert [count_visible(pool, tenants["a"], t) for t in ("tenant", "client", "app_user")] == [1, 1, 1]
    with with_tenant(pool, TenantScope(tenants["a"])) as db:
        assert [r["name"] for r in db.execute("SELECT name FROM identity.client")] == ["Client of A"]


def test_cannot_read_another_tenants_rows_by_id(pool, tenants):
    with with_tenant(pool, TenantScope(tenants["a"])) as db:
        assert db.execute("SELECT id FROM identity.tenant WHERE id = %s", (tenants["b"],)).fetchall() == []


def test_cannot_write_rows_into_another_tenant(pool, tenants):
    def insert():
        with with_tenant(pool, TenantScope(tenants["a"])) as db:
            db.execute("INSERT INTO identity.client (agency_tenant_id, name) VALUES (%s, 'Sneaky')", (tenants["b"],))

    assert "row-level security" in str(rejected(insert))
    with with_tenant(pool, TenantScope(tenants["a"])) as db:
        updated = db.execute("UPDATE identity.client SET name = 'Hijacked' WHERE agency_tenant_id = %s", (tenants["b"],))
        assert updated.rowcount == 0


def test_rejects_a_client_under_a_direct_employer_tenant(pool, tenants):
    assert rejected(lambda: create_client(pool, tenants["employer"], "Not allowed")).sqlstate == "TM003"


def test_does_not_allow_changing_a_tenants_org_type(pool, tenants):
    def change():
        with with_tenant(pool, TenantScope(tenants["employer"])) as db:
            db.execute("UPDATE identity.tenant SET org_type = 'staffing_agency' WHERE id = %s", (tenants["employer"],))

    assert rejected(change).sqlstate == "TM004"


def test_keeps_email_unique_within_a_tenant_but_not_across_tenants(pool, tenants):
    assert rejected(lambda: create_user(pool, tenants["a"], "MANAGER@agency-a.test")).sqlstate == "23505"
    create_user(pool, tenants["b"], "manager@agency-a.test")


def test_allows_a_password_hash_only_for_local_password_users(pool, tenants):
    def insert():
        with with_tenant(pool, TenantScope(tenants["a"])) as db:
            db.execute(
                """INSERT INTO identity.app_user (tenant_id, email, auth_method, password_hash, role)
                   VALUES (%s, 'sso@a.test', 'sso_google', 'x', 'manager')""",
                (tenants["a"],),
            )

    assert rejected(insert).sqlstate == "23514"


def test_does_not_let_svc_auth_see_the_migration_history(pool):
    def read():
        with pool.connection() as db:
            db.execute("SELECT * FROM identity.schema_migrations")

    assert "permission denied" in str(rejected(read))
