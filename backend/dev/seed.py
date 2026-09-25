"""Loads demo data into the LOCAL database for manual checks.

Usage (from backend/, with the venv active; requisition-service must be running):
    python dev/seed.py            -> seeds once; later runs report what's there
    python dev/seed.py --force    -> adds another set of demo requisitions

1. Demo tenants, clients and users are inserted directly (there is no admin API yet) as the PostgreSQL
   superuser from backend/.env (PGHOST/PGPORT/PGUSER/PGPASSWORD). Safe to re-run.
2. Demo requisitions, JD versions and scoring matrices are created THROUGH THE API, so every business
   rule (HR-M1-FR-007/004/006) applies to them exactly as to real data.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

import psycopg
from demo import CLIENTS, ENV_FILE, REQUISITION_API, TENANTS, USERS

from teamora_common import AuthContext, load_env_file, sign_access_token


def main() -> None:
    if ENV_FILE.exists():
        load_env_file(ENV_FILE)
    if os.environ.get("APP_ENV") != "local":
        sys.exit(f"Refusing: demo data is for APP_ENV=local only (APP_ENV={os.environ.get('APP_ENV')}).")

    tenant_ids = [t["id"] for t in TENANTS.values()]
    with psycopg.connect(dbname="teamora") as db:  # PGHOST/PGPORT/PGUSER/PGPASSWORD from backend/.env
        seed_identity(db)
        existing = db.execute(
            "SELECT count(*) FROM requisition.job_requisition WHERE tenant_id = ANY(%s)", (tenant_ids,)
        ).fetchone()[0]
        if existing and "--force" not in sys.argv:
            print(f"\nDemo requisitions already exist ({existing}). Use `python dev/seed.py --force` to add another set.")
        else:
            assert_api_up()
            seed_requisitions()
        print_summary(db, tenant_ids)


def seed_identity(db: psycopg.Connection) -> None:
    for t in TENANTS.values():
        db.execute(
            "INSERT INTO identity.tenant (id, org_type, name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (t["id"], t["org_type"], t["name"]),
        )
    for c in CLIENTS.values():
        db.execute(
            "INSERT INTO identity.client (id, agency_tenant_id, name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (c["id"], TENANTS[c["tenant"]]["id"], c["name"]),
        )
    for u in USERS.values():
        db.execute(
            """INSERT INTO identity.app_user (id, tenant_id, email, auth_method, role)
               VALUES (%s, %s, %s, 'sso_google', %s) ON CONFLICT DO NOTHING""",
            (u["id"], TENANTS[u["tenant"]]["id"], u["email"], u["role"]),
        )
    db.commit()
    print("Identity: 2 tenants, 2 agency clients, 2 managers - ready.")


def assert_api_up() -> None:
    try:
        with urllib.request.urlopen(f"{REQUISITION_API}/health/ready", timeout=5):
            return
    except (urllib.error.URLError, OSError):
        pass
    sys.exit(
        f"requisition-service is not reachable at {REQUISITION_API}. Start it first: "
        "python -m requisition_service --env-file .env"
    )


def api_as(who: str):
    user = USERS[who]
    auth = AuthContext(user_id=user["id"], tenant_id=TENANTS[user["tenant"]]["id"], role=user["role"])
    token = sign_access_token(os.environ["AUTH_JWT_SECRET"], auth, 600)

    def call(method: str, path: str, body: dict | None = None) -> dict:
        request = urllib.request.Request(
            f"{REQUISITION_API}/api/v1{path}",
            method=method,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as res:
                return json.loads(res.read() or b"null")
        except urllib.error.HTTPError as err:
            raise SystemExit(f"{method} {path} -> {err.code} {err.read().decode()}") from err

    return call


def add_criteria(call, r: str, v: str, criteria) -> int:
    revision = call("GET", f"/requisitions/{r}/jd-versions/{v}/scoring-matrix/draft")["matrix_revision"]
    for category, name, weight in criteria:
        revision = call(
            "POST",
            f"/requisitions/{r}/jd-versions/{v}/scoring-matrix/draft/criteria",
            {"matrix_revision": revision, "category": category, "criterion_name": name, "weight_percent": weight},
        )["matrix_revision"]
    return revision


def requisition_with_version(call, *, tenant, client, brief, jd, variant, criteria=()) -> tuple[str, str]:
    r = call(
        "POST",
        "/requisitions/intake",
        {
            "tenant_id": TENANTS[tenant]["id"],
            "client_id": CLIENTS[client]["id"] if client else None,
            "raw_brief_text": brief,
            "source": "portal",
        },
    )["requisition_id"]
    v = call("POST", f"/requisitions/{r}/jd-versions", {"content": jd, "variant_type": variant})["id"]
    add_criteria(call, r, v, criteria)
    return r, v


def seed_requisitions() -> None:
    agency, employer = api_as("agency"), api_as("employer")

    # 1. Agency / Retail Co: frozen v1, plus a v2 revision under review whose matrix totals only 90%.
    r, v = requisition_with_version(
        agency,
        tenant="agency",
        client="retail",
        brief="Need a senior data analyst for Retail Co: Power BI, SQL, 5+ years, retail domain, graduate.",
        jd=(
            "Senior Data Analyst (Retail Co). Own sales and inventory dashboards in Power BI; write production SQL; "
            "partner with category managers. 5+ years of analytics experience in retail."
        ),
        variant="formal",
        criteria=[
            ("core_skills", "Power BI and SQL", 45),
            ("experience_seniority", "5+ years analytics", 30),
            ("domain_competency", "Retail / category management", 20),
            ("education_fit", "Graduate degree", 5),
        ],
    )
    agency("POST", f"/requisitions/{r}/jd-versions/{v}/submit")
    agency("POST", f"/requisitions/{r}/freeze", {"approved_version_id": v, "expected_active_version_id": None})
    v2 = agency(
        "POST",
        f"/requisitions/{r}/jd-versions",
        {
            "content": "Senior Data Analyst (Retail Co) - revised: adds Python for forecasting; hybrid, 3 days on site.",
            "variant_type": "manager_edited",
            "based_on_version_id": v,
        },
    )["id"]
    add_criteria(
        agency,
        r,
        v2,
        [("core_skills", "Power BI, SQL and Python", 60), ("experience_seniority", "5+ years analytics", 30)],
    )

    # 2. Agency / Fintech Co: just a first draft, empty matrix.
    requisition_with_version(
        agency,
        tenant="agency",
        client="fintech",
        brief="Fintech Co wants a backend engineer - Python, PostgreSQL, payments experience a plus.",
        jd="Backend Engineer (Fintech Co). Build payment APIs in Python and PostgreSQL. 3+ years.",
        variant="candidate_friendly",
    )

    # 3. Direct employer: waiting for approval with a complete (100%) matrix - ready for you to freeze.
    r, v = requisition_with_version(
        employer,
        tenant="employer",
        client=None,
        brief="HR executive for our Pune office: onboarding, payroll coordination, 2-4 years.",
        jd="HR Executive (Pune). Run onboarding end to end and coordinate payroll inputs. 2-4 years in HR operations.",
        variant="formal",
        criteria=[
            ("core_skills", "Onboarding and HR operations", 50),
            ("experience_seniority", "2-4 years HR", 25),
            ("domain_competency", "Payroll coordination", 20),
            ("education_fit", "MBA / PG in HR", 5),
        ],
    )
    employer("POST", f"/requisitions/{r}/jd-versions/{v}/submit")
    print("Demo requisitions created through the API.")


def print_summary(db: psycopg.Connection, tenant_ids: list[str]) -> None:
    rows = db.execute(
        """SELECT t.name, coalesce(c.name, '-'), r.id::text, r.status,
                  (SELECT count(*) FROM requisition.jd_version v WHERE v.requisition_id = r.id)
             FROM requisition.job_requisition r
             JOIN identity.tenant t ON t.id = r.tenant_id
             LEFT JOIN identity.client c ON c.id = r.client_id
            WHERE r.tenant_id = ANY(%s)
            ORDER BY r.created_at""",
        (tenant_ids,),
    ).fetchall()
    print("\nDemo requisitions:")
    print(f"  {'tenant':<22} {'client':<26} {'id':<38} {'status':<16} versions")
    for tenant, client, rid, status, versions in rows:
        print(f"  {tenant:<22} {client:<26} {rid:<38} {status:<16} {versions}")
    print(f"\nBrowse them: {REQUISITION_API}/api/docs  (Authorize with a token from `python dev/make_token.py`)")


if __name__ == "__main__":
    main()
