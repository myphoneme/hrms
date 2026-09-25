"""HR-M1-FR-007 acceptance scenarios (BRD §4.1) and requisition isolation, against a real database."""

import uuid

import psycopg
import pytest

from teamora_common import TenantScope, with_tenant

pytestmark = pytest.mark.db

BRIEF = "Senior data analyst, Power BI, 5+ years"


@pytest.fixture(scope="module")
def world(id_pool, helpers):
    agency = helpers.create_tenant(id_pool, "staffing_agency")
    other_agency = helpers.create_tenant(id_pool, "staffing_agency")
    return {
        "agency": agency,
        "agency_client": helpers.create_client(id_pool, agency),
        "other_agency": other_agency,
        "other_agency_client": helpers.create_client(id_pool, other_agency),
        "employer": helpers.create_tenant(id_pool, "direct_employer"),
    }


@pytest.fixture
def intake(client, helpers):
    def call(auth, **body):
        payload = {"tenant_id": auth.tenant_id, "raw_brief_text": BRIEF, "source": "portal", **body}
        return helpers.Api(client, auth).post("/api/v1/requisitions/intake", payload)

    return call


def read_requisition(req_pool, tenant_id, requisition_id):
    with with_tenant(req_pool, TenantScope(tenant_id)) as db:
        return db.execute(
            """SELECT r.tenant_id, r.client_id, r.status, r.created_by, b.raw_text, b.source
                 FROM requisition.job_requisition r JOIN requisition.jd_brief b ON b.requisition_id = r.id
                WHERE r.id = %s""",
            (requisition_id,),
        ).fetchone()


def count_requisitions(req_pool, tenant_id):
    with with_tenant(req_pool, TenantScope(tenant_id)) as db:
        return db.execute("SELECT count(*)::int AS n FROM requisition.job_requisition").fetchone()["n"]


# BRD §4.1 acceptance scenario: agency manager submits a brief without selecting a client.
def test_rejects_an_agency_brief_without_a_client(world, intake, helpers):
    res = intake(helpers.manager_of(world["agency"]), client_id=None)
    assert res.status_code == 422
    assert res.json()["reason"] == "client_required"


# BRD §4.1 acceptance scenario: direct-employer manager submits a brief with a client selected.
def test_rejects_a_direct_employer_brief_with_a_client(world, intake, helpers):
    res = intake(helpers.manager_of(world["employer"]), client_id=world["agency_client"])
    assert res.status_code == 422
    assert res.json()["reason"] == "client_not_allowed"


def test_creates_a_draft_requisition_and_its_brief_for_an_agency_with_its_own_client(world, intake, helpers, req_pool):
    auth = helpers.manager_of(world["agency"])
    res = intake(auth, client_id=world["agency_client"])
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "Draft"
    assert read_requisition(req_pool, world["agency"], body["requisition_id"]) == {
        "tenant_id": world["agency"],
        "client_id": world["agency_client"],
        "status": "Draft",
        "created_by": auth.user_id,
        "raw_text": BRIEF,
        "source": "portal",
    }


def test_creates_a_draft_requisition_for_a_direct_employer_with_null_client(world, intake, helpers, req_pool):
    res = intake(helpers.manager_of(world["employer"]), client_id=None, source="email")
    assert res.status_code == 201
    row = read_requisition(req_pool, world["employer"], res.json()["requisition_id"])
    assert (row["client_id"], row["source"]) == (None, "email")


def test_rejects_another_agencys_client(world, intake, helpers):
    res = intake(helpers.manager_of(world["agency"]), client_id=world["other_agency_client"])
    assert res.status_code == 422
    assert res.json()["reason"] == "unknown_client"


def test_rejects_a_client_id_that_does_not_exist(world, intake, helpers):
    res = intake(helpers.manager_of(world["agency"]), client_id=str(uuid.uuid4()))
    assert res.status_code == 422
    assert res.json()["reason"] == "unknown_client"


def test_writes_nothing_when_a_brief_is_rejected(world, intake, helpers, req_pool):
    before = count_requisitions(req_pool, world["agency"])
    assert intake(helpers.manager_of(world["agency"]), client_id=None).status_code == 422
    assert count_requisitions(req_pool, world["agency"]) == before


def test_enforces_the_rule_in_the_database_even_without_the_api(world, req_pool):
    with pytest.raises(psycopg.Error) as exc, with_tenant(req_pool, TenantScope(world["agency"])) as db:
        db.execute(
            "INSERT INTO requisition.job_requisition (tenant_id, client_id, created_by) VALUES (%s, NULL, %s)",
            (world["agency"], str(uuid.uuid4())),
        )
    assert exc.value.sqlstate == "TM001"


def test_never_shows_one_tenant_another_tenants_requisitions(world, intake, helpers, req_pool):
    res = intake(helpers.manager_of(world["agency"]), client_id=world["agency_client"])
    requisition_id = res.json()["requisition_id"]
    assert read_requisition(req_pool, world["other_agency"], requisition_id) is None
    assert read_requisition(req_pool, world["employer"], requisition_id) is None
    with req_pool.connection() as db:
        # No tenant scope -> zero rows.
        assert db.execute("SELECT count(*)::int AS n FROM requisition.job_requisition").fetchone()["n"] == 0


def test_scopes_to_one_client_when_the_request_is_client_scoped(world, intake, helpers, req_pool):
    res = intake(helpers.manager_of(world["agency"]), client_id=world["agency_client"])
    with with_tenant(req_pool, TenantScope(world["agency"], client_id=str(uuid.uuid4()))) as db:
        seen = db.execute("SELECT 1 FROM requisition.job_requisition WHERE id = %s", (res.json()["requisition_id"],)).fetchall()
    assert seen == []
