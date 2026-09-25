"""HR-M1-FR-004 — JD versioning & audit trail (TDD §6.0, §6, §8, §15).

Every edit is stored as a new version with author and timestamp; versions are never edited in place.
The database enforces this too: content is immutable, only the TDD §6.0 status transitions are allowed,
and versions can't be deleted.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

import psycopg
from fastapi import APIRouter, Body
from pydantic import BaseModel

from teamora_common import ApiError, Auth, with_tenant
from teamora_common.validation import Uuid, text

from .common import Pool, not_found, require_id, tenant_scope_of

#: Upper bound on one JD version's text.
MAX_JD_LENGTH = 50_000

VERSION_COLUMNS = """id, requisition_id, version_no, variant_type, generated_by, status,
  based_on_version_id, superseded_by, created_by, created_at, content"""

#: Requisition states in which JD work can no longer happen.
CLOSED_STATES = ("OnHold", "Closed")

router = APIRouter(prefix="/requisitions/{requisition_id}/jd-versions", tags=["HR-M1-FR-004 · JD versions"])


class CreateVersionRequest(BaseModel):
    content: text(MAX_JD_LENGTH)
    #: Defaults to manager_edited.
    variant_type: Literal["formal", "candidate_friendly", "condensed", "manager_edited"] | None = None
    #: The version being revised; null for a first draft.
    based_on_version_id: Uuid | None = None


EXAMPLE = {
    "content": "Senior Data Analyst — you will own retail sales dashboards in Power BI…",
    "variant_type": "formal",
    "based_on_version_id": None,
}


@router.get("", summary="Full version history (Approved / Superseded / Rejected included)")
def list_versions(requisition_id: str, auth: Auth, pool: Pool) -> list[dict[str, Any]]:
    requisition_id = require_id(requisition_id, "requisition")
    with with_tenant(pool, tenant_scope_of(auth)) as db:
        find_requisition(db, requisition_id, lock=False)
        rows = db.execute(
            f"SELECT {VERSION_COLUMNS} FROM requisition.jd_version WHERE requisition_id = %s ORDER BY version_no",
            (requisition_id,),
        ).fetchall()
    return [_dto(row) for row in rows]


@router.post(
    "",
    status_code=201,
    summary="Every edit is a new version (first = Draft; with based_on_version_id = Revising)",
)
def create_version(
    requisition_id: str,
    body: Annotated[CreateVersionRequest, Body(openapi_examples={"first draft": {"value": EXAMPLE}})],
    auth: Auth,
    pool: Pool,
) -> dict[str, Any]:
    requisition_id = require_id(requisition_id, "requisition")
    status = "Revising" if body.based_on_version_id else "Draft"
    try:
        with with_tenant(pool, tenant_scope_of(auth)) as db:
            requisition = find_requisition(db, requisition_id, lock=True)
            assert_open(requisition["status"])
            row = db.execute(
                f"""INSERT INTO requisition.jd_version
                      (requisition_id, version_no, variant_type, content, generated_by, status, based_on_version_id, created_by)
                    SELECT %(r)s, coalesce(max(version_no), 0) + 1, %(variant)s, %(content)s, 'manager',
                           %(status)s, %(base)s, %(user)s
                      FROM requisition.jd_version WHERE requisition_id = %(r)s
                    RETURNING {VERSION_COLUMNS}""",
                {
                    "r": requisition_id,
                    "variant": body.variant_type or "manager_edited",
                    "content": body.content,
                    "status": status,
                    "base": body.based_on_version_id,
                    "user": auth.user_id,
                },
            ).fetchone()
            # Before the first freeze, the requisition follows its review loop (TDD §6.0).
            if status == "Revising" and requisition["status"] == "PendingApproval":
                set_requisition_status(db, requisition_id, "Revising")
    except psycopg.Error as exc:
        if exc.sqlstate == "TM013":
            raise ApiError(422, "unknown_base_version", "based_on_version_id is not a version of this requisition.") from exc
        raise
    return _dto(row)


@router.post("/{version_id}/submit", summary="Send a Draft/Revising version for approval (-> PendingApproval)")
def submit_version(requisition_id: str, version_id: str, auth: Auth, pool: Pool) -> dict[str, Any]:
    requisition_id = require_id(requisition_id, "requisition")
    version_id = require_id(version_id, "version")
    with with_tenant(pool, tenant_scope_of(auth)) as db:
        requisition = find_requisition(db, requisition_id, lock=True)
        assert_open(requisition["status"])
        version = db.execute(
            "SELECT status FROM requisition.jd_version WHERE id = %s AND requisition_id = %s FOR UPDATE",
            (version_id, requisition_id),
        ).fetchone()
        if version is None:
            raise not_found("version")
        if version["status"] not in ("Draft", "Revising"):
            raise ApiError(
                409,
                "version_not_submittable",
                f"Only a Draft or Revising version can be sent for approval; this one is {version['status']}.",
                {"current_status": version["status"]},
            )
        row = db.execute(
            f"UPDATE requisition.jd_version SET status = 'PendingApproval' WHERE id = %s RETURNING {VERSION_COLUMNS}",
            (version_id,),
        ).fetchone()
        if requisition["status"] in ("Draft", "Revising"):
            set_requisition_status(db, requisition_id, "PendingApproval")
    return _dto(row)


@router.patch("/{version_id}", summary="Always 409 version_immutable — versions are never edited in place")
def edit_version(requisition_id: str, version_id: str) -> None:
    # HR-M1-FR-004; TDD §15 "Manager attempts to edit a frozen JD": point to the correct path instead.
    raise ApiError(
        409,
        "version_immutable",
        "JD versions are never edited in place. Create a new version based on this one instead.",
        {
            "create_new_version": f"POST /api/v1/requisitions/{requisition_id}/jd-versions",
            "based_on_version_id": version_id,
        },
    )


def find_requisition(db: psycopg.Connection, requisition_id: str, lock: bool) -> dict[str, Any]:
    row = db.execute(
        "SELECT status FROM requisition.job_requisition WHERE id = %s" + (" FOR UPDATE" if lock else ""),
        (requisition_id,),
    ).fetchone()
    if row is None:
        raise not_found("requisition")
    return row


def assert_open(status: str) -> None:
    if status in CLOSED_STATES:
        raise ApiError(
            409,
            "requisition_not_editable",
            f"The requisition is {status}; its JD can't be changed.",
            {"requisition_status": status},
        )


def set_requisition_status(db: psycopg.Connection, requisition_id: str, status: str) -> None:
    db.execute(
        "UPDATE requisition.job_requisition SET status = %s, updated_at = now() WHERE id = %s",
        (status, requisition_id),
    )


def _dto(row: dict[str, Any]) -> dict[str, Any]:
    return {**row, "created_at": row["created_at"].isoformat()}
