"""HR-M1-FR-007 — requisition intake: POST /api/v1/requisitions/intake (TDD §8, §12.1 step 2).

An agency tenant must name one of its own end-clients; a direct employer must send ``client_id: null``.
The org_type rule itself is enforced by the database (triggers TM001/TM002), so it holds even
without this API; this layer checks the request shape and the caller's tenant.
"""

from __future__ import annotations

from typing import Annotated, Literal

import psycopg
from fastapi import APIRouter, Body
from pydantic import BaseModel

from teamora_common import MISSING_FIELD_HINTS, ApiError, Auth, TenantScope, with_tenant
from teamora_common.validation import Uuid, text

from .common import Pool

#: Upper bound on a raw brief, so a single request can't store an unbounded text blob.
MAX_BRIEF_LENGTH = 20_000

# Omitting client_id is always an error; null is a valid value (TDD §5.2).
MISSING_FIELD_HINTS["client_id"] = "is required (use null for a direct-employer tenant)"

router = APIRouter(prefix="/requisitions", tags=["HR-M1-FR-007 · Requisition intake"])


class IntakeRequest(BaseModel):
    tenant_id: Uuid
    #: Required, but may be null (direct employer).
    client_id: Uuid | None
    department_id: Uuid | None = None
    raw_brief_text: text(MAX_BRIEF_LENGTH)
    source: Literal["email", "portal"]


EXAMPLE = {
    "tenant_id": "11111111-1111-4111-8111-111111111111",
    "client_id": "22222222-2222-4222-8222-222222222222",
    "department_id": None,
    "raw_brief_text": "Need a senior data analyst: Power BI, SQL, 5+ years, retail domain.",
    "source": "portal",
}


@router.post(
    "/intake",
    status_code=201,
    summary="Create a Draft requisition from a raw brief (agency: client required; direct employer: client_id null)",
)
def intake(
    body: Annotated[IntakeRequest, Body(openapi_examples={"agency": {"value": EXAMPLE}})],
    auth: Auth,
    pool: Pool,
) -> dict:
    if auth.tenant_id is None:
        raise ApiError(
            403,
            "tenant_scope_required",
            "Requisitions are created within a tenant; a platform admin token has no tenant scope.",
        )
    # Every token carries tenant_id; a request for any other tenant is rejected (TDD §3.1).
    if body.tenant_id.lower() != auth.tenant_id.lower():
        raise ApiError(403, "tenant_mismatch", "tenant_id does not match the caller's tenant.")

    try:
        with with_tenant(pool, TenantScope(tenant_id=auth.tenant_id)) as db:
            requisition_id = db.execute(
                """INSERT INTO requisition.job_requisition (tenant_id, client_id, department_id, created_by)
                   VALUES (%s, %s, %s, %s) RETURNING id""",
                (auth.tenant_id, body.client_id, body.department_id, auth.user_id),
            ).fetchone()["id"]
            db.execute(
                "INSERT INTO requisition.jd_brief (requisition_id, raw_text, source) VALUES (%s, %s, %s)",
                (requisition_id, body.raw_brief_text, body.source),
            )
    except psycopg.Error as exc:
        translated = _translate(exc)
        if translated is None:
            raise
        raise translated from exc
    return {"requisition_id": requisition_id, "status": "Draft"}


def _translate(exc: psycopg.Error) -> ApiError | None:
    """Maps the database's HR-M1-FR-007 and isolation rejections to API errors; anything else is a 500."""
    if exc.sqlstate == "TM001":
        return ApiError(
            422,
            "client_required",
            "This tenant is a staffing agency: the requisition must specify the end-client (client_id).",
        )
    if exc.sqlstate == "TM002":
        return ApiError(422, "client_not_allowed", "This tenant is a direct employer: client_id must be null.")
    if exc.sqlstate == "23503":
        constraint = exc.diag.constraint_name
        if constraint == "job_requisition_client_fkey":
            return ApiError(422, "unknown_client", "client_id does not identify a client of this tenant.")
        if constraint == "job_requisition_tenant_fkey":
            return ApiError(403, "unknown_tenant", "The caller's tenant does not exist.")
    return None
