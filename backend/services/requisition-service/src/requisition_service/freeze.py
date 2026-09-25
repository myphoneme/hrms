"""HR-M1-FR-006 — freeze: POST /api/v1/requisitions/{id}/freeze (TDD §8, §12.1 steps 8-9).

Approves one PendingApproval JD version and its draft matrix in ONE transaction, supersedes the
previously approved version (kept, never overwritten) and repoints the requisition. The requisition
row lock serialises concurrent freezes: exactly one wins.
"""

from __future__ import annotations

from typing import Annotated, Any

import psycopg
from fastapi import APIRouter, Body
from pydantic import BaseModel

from teamora_common import MISSING_FIELD_HINTS, ApiError, Auth, with_tenant
from teamora_common.validation import Uuid

from .common import Pool, not_found, require_id, tenant_scope_of
from .scoring_matrix import load_matrix

MISSING_FIELD_HINTS["expected_active_version_id"] = "is required (null if the requisition was never frozen)"

router = APIRouter(prefix="/requisitions/{requisition_id}", tags=["HR-M1-FR-006 · Scoring matrix"])


class FreezeRequest(BaseModel):
    approved_version_id: Uuid
    #: Required, but may be null (the requisition was never frozen).
    expected_active_version_id: Uuid | None


@router.post("/freeze", summary="Freeze: approve a PendingApproval version + its matrix (weights must total 100%)")
def freeze(
    requisition_id: str,
    body: Annotated[
        FreezeRequest,
        Body(
            openapi_examples={
                "first freeze": {
                    "value": {"approved_version_id": "<PendingApproval version id>", "expected_active_version_id": None}
                }
            }
        ),
    ],
    auth: Auth,
    pool: Pool,
) -> dict[str, Any]:
    requisition_id = require_id(requisition_id, "requisition")
    approved = body.approved_version_id
    with with_tenant(pool, tenant_scope_of(auth)) as db:
        requisition = db.execute(
            "SELECT status, active_version_id FROM requisition.job_requisition WHERE id = %s FOR UPDATE",
            (requisition_id,),
        ).fetchone()
        if requisition is None:
            raise not_found("requisition")
        active = requisition["active_version_id"]

        # Exact repeat of a freeze that already succeeded: 200 no-op, same response (TDD §8 idempotency).
        if active == approved:
            return _result_for(db, requisition["status"], approved)
        if requisition["status"] in ("OnHold", "Closed"):
            raise ApiError(409, "requisition_not_editable", f"The requisition is {requisition['status']}; it can't be frozen.")
        # Someone else's freeze landed first (TDD §8): exactly one concurrent caller's expectation matches.
        if active != body.expected_active_version_id:
            raise ApiError(
                409,
                "stale_expected_version",
                "The requisition was frozen by someone else since you last read it.",
                current_active_version_id=active,
            )

        version = db.execute(
            "SELECT status FROM requisition.jd_version WHERE id = %s AND requisition_id = %s FOR UPDATE",
            (approved, requisition_id),
        ).fetchone()
        if version is None or version["status"] != "PendingApproval":
            raise ApiError(
                409,
                "version_not_approvable",
                "Only a version awaiting approval (PendingApproval) can be frozen.",
                {"current_status": version["status"] if version else None},
            )

        # Weights must total exactly 100 — rejected with the offending total, never normalised (BRD §5).
        locked = db.execute(
            "SELECT 1 FROM requisition.scoring_matrix WHERE jd_version_id = %s FOR UPDATE", (approved,)
        ).fetchone()
        matrix = load_matrix(db, approved) if locked else None
        if matrix is None or matrix["current_total_percent"] != 100:
            raise ApiError(
                409,
                "matrix_total_invalid",
                "The scoring matrix weights must total exactly 100% before freezing.",
                {"current_total_percent": matrix["current_total_percent"] if matrix else 0},
            )

        # Supersede first: at most one Approved version per requisition at any moment.
        if active is not None:
            db.execute(
                "UPDATE requisition.jd_version SET status = 'Superseded', superseded_by = %s WHERE id = %s", (approved, active)
            )
        db.execute("UPDATE requisition.jd_version SET status = 'Approved' WHERE id = %s", (approved,))
        db.execute(
            "UPDATE requisition.scoring_matrix SET status = 'Approved', approved_at = now() WHERE id = %s",
            (matrix["matrix_id"],),
        )
        db.execute(
            """UPDATE requisition.job_requisition
                  SET active_version_id = %s, status = 'Frozen_Open', updated_at = now() WHERE id = %s""",
            (approved, requisition_id),
        )
        # The requisition.frozen event for the Module 2 Publish Service (TDD §12.1 step 10) follows with the event backbone.
        return {
            "status": "Frozen_Open",
            "active_version_id": approved,
            "scoring_matrix_id": matrix["matrix_id"],
            "superseded_version_id": active,
        }


def _result_for(db: psycopg.Connection, status: str, active_version_id: str) -> dict[str, Any]:
    matrix = db.execute("SELECT id FROM requisition.scoring_matrix WHERE jd_version_id = %s", (active_version_id,)).fetchone()
    superseded = db.execute("SELECT id FROM requisition.jd_version WHERE superseded_by = %s", (active_version_id,)).fetchone()
    return {
        "status": status,
        "active_version_id": active_version_id,
        "scoring_matrix_id": matrix["id"],
        "superseded_version_id": superseded["id"] if superseded else None,
    }
