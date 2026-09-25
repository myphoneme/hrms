"""HR-M1-FR-006 — draft scoring matrix of a JD version, and the Approved matrix (TDD §6, §8).

Weights are checked per criterion here; the sum-to-100 rule is enforced only at freeze (freeze.py),
so a partial draft can be saved. Every edit must quote the ``matrix_revision`` it was made against
(optimistic concurrency), so two browser tabs can't silently overwrite each other.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from decimal import Decimal
from typing import Annotated, Any, Literal, TypeVar

import psycopg
from fastapi import APIRouter, Body
from pydantic import BaseModel, PlainValidator, WithJsonSchema, field_validator

from teamora_common import ApiError, Auth, AuthContext, unprocessable, with_tenant
from teamora_common.validation import Uuid, text

from .common import Pool, not_found, require_id, tenant_scope_of

T = TypeVar("T")

#: JD version states whose matrix is still a working draft.
OPEN_VERSION_STATES = ("Draft", "Revising", "PendingApproval")

#: Screening categories only — soft skills are never scored numerically at this stage (BRD §4.1).
Category = Literal["core_skills", "experience_seniority", "domain_competency", "education_fit"]


def _weight(value: Any) -> float:
    """0-100 with at most two decimals. Compared with a tolerance: 33.33 * 100 is 3332.9999999999995."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 <= value <= 100
        or abs(round(value * 100) - value * 100) >= 1e-6
    ):
        raise ValueError("must be a number from 0 to 100 with at most two decimals")
    return value


Weight = Annotated[float, PlainValidator(_weight), WithJsonSchema({"type": "number", "minimum": 0, "maximum": 100})]


def _revision(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("must be a positive integer (the revision you last read)")
    return value


Revision = Annotated[int, PlainValidator(_revision), WithJsonSchema({"type": "integer", "minimum": 1})]


class WeightEdit(BaseModel):
    criterion_id: Uuid
    weight_percent: Weight


class EditWeightsRequest(BaseModel):
    matrix_revision: Revision
    criteria: list[WeightEdit]

    @field_validator("criteria")
    @classmethod
    def _non_empty_unique(cls, value: list[WeightEdit]) -> list[WeightEdit]:
        if not value:
            raise ValueError("must be a non-empty array")
        ids = [c.criterion_id for c in value]
        if len(set(ids)) != len(ids):
            raise ValueError("must not repeat a criterion_id")
        return value


class AddCriterionRequest(BaseModel):
    matrix_revision: Revision
    category: Category
    criterion_name: text(200)
    weight_percent: Weight


router = APIRouter(prefix="/requisitions/{requisition_id}", tags=["HR-M1-FR-006 · Scoring matrix"])
DRAFT = "/jd-versions/{version_id}/scoring-matrix/draft"


@router.get(DRAFT, summary="The draft matrix of a JD version (created empty on first read)")
def get_draft(requisition_id: str, version_id: str, auth: Auth, pool: Pool) -> dict[str, Any]:
    requisition_id, version_id = require_id(requisition_id, "requisition"), require_id(version_id, "version")
    with with_tenant(pool, tenant_scope_of(auth)) as db:
        version = find_version(db, requisition_id, version_id, lock=False)
        exists = db.execute("SELECT 1 FROM requisition.scoring_matrix WHERE jd_version_id = %s", (version_id,)).fetchone()
        if exists is None:
            # In production the JD Generation worker fills it (HR-M1-FR-001/002); until then it starts empty.
            if version["status"] not in OPEN_VERSION_STATES:
                raise matrix_not_found()
            db.execute(
                "INSERT INTO requisition.scoring_matrix (jd_version_id) VALUES (%s) ON CONFLICT (jd_version_id) DO NOTHING",
                (version_id,),
            )
        return load_matrix(db, version_id)


@router.patch(DRAFT, summary="Adjust weights (total checked only at freeze); matrix_revision must be the one you last read")
def edit_weights(
    requisition_id: str,
    version_id: str,
    body: Annotated[
        EditWeightsRequest,
        Body(
            openapi_examples={
                "adjust": {
                    "value": {
                        "matrix_revision": 5,
                        "criteria": [{"criterion_id": "<criterion id from GET>", "weight_percent": 40}],
                    }
                }
            }
        ),
    ],
    auth: Auth,
    pool: Pool,
) -> dict[str, Any]:
    def apply(db: psycopg.Connection, matrix_id: str) -> dict[str, Any]:
        known = {r["id"] for r in db.execute("SELECT id FROM requisition.scoring_criterion WHERE matrix_id = %s", (matrix_id,))}
        unknown = [c.criterion_id for c in body.criteria if c.criterion_id not in known]
        if unknown:
            raise ApiError(
                422, "unknown_criterion", "Some criterion_id values are not part of this matrix.", {"criterion_ids": unknown}
            )
        for c in body.criteria:
            db.execute(
                "UPDATE requisition.scoring_criterion SET weight_percent = %s WHERE id = %s", (c.weight_percent, c.criterion_id)
            )
        matrix = bump_revision(db, matrix_id, version_id)
        return {k: matrix[k] for k in ("status", "matrix_revision", "current_total_percent")}

    return _with_draft(auth, pool, requisition_id, version_id, body.matrix_revision, apply)


@router.post(
    DRAFT + "/criteria",
    status_code=201,
    summary="Add a criterion (categories: core_skills, experience_seniority, domain_competency, education_fit)",
)
def add_criterion(
    requisition_id: str,
    version_id: str,
    body: Annotated[
        AddCriterionRequest,
        Body(
            openapi_examples={
                "core skill": {
                    "value": {
                        "matrix_revision": 1,
                        "category": "core_skills",
                        "criterion_name": "Power BI proficiency",
                        "weight_percent": 45,
                    }
                }
            }
        ),
    ],
    auth: Auth,
    pool: Pool,
) -> dict[str, Any]:
    def apply(db: psycopg.Connection, matrix_id: str) -> dict[str, Any]:
        db.execute(
            """INSERT INTO requisition.scoring_criterion (matrix_id, category, criterion_name, weight_percent)
               VALUES (%s, %s, %s, %s)""",
            (matrix_id, body.category, body.criterion_name.strip(), body.weight_percent),
        )
        return bump_revision(db, matrix_id, version_id)

    return _with_draft(auth, pool, requisition_id, version_id, body.matrix_revision, apply)


@router.delete(DRAFT + "/criteria/{criterion_id}", summary="Remove a criterion (?matrix_revision=N)")
def remove_criterion(
    requisition_id: str, version_id: str, criterion_id: str, auth: Auth, pool: Pool, matrix_revision: str | None = None
) -> dict[str, Any]:
    criterion_id = require_id(criterion_id, "criterion")
    try:
        revision = int(matrix_revision or "")
    except ValueError:
        revision = 0
    if revision < 1:
        raise unprocessable([{"field": "matrix_revision", "problem": "query parameter must be a positive integer"}])

    def apply(db: psycopg.Connection, matrix_id: str) -> dict[str, Any]:
        deleted = db.execute(
            "DELETE FROM requisition.scoring_criterion WHERE id = %s AND matrix_id = %s", (criterion_id, matrix_id)
        ).rowcount
        if deleted == 0:
            raise not_found("criterion")
        return bump_revision(db, matrix_id, version_id)

    return _with_draft(auth, pool, requisition_id, version_id, revision, apply)


@router.get("/scoring-matrix", summary="The Approved matrix of the active version (after freeze)")
def get_approved(requisition_id: str, auth: Auth, pool: Pool) -> dict[str, Any]:
    """What Module 3 scores candidates against (TDD §8)."""
    requisition_id = require_id(requisition_id, "requisition")
    with with_tenant(pool, tenant_scope_of(auth)) as db:
        row = db.execute("SELECT active_version_id FROM requisition.job_requisition WHERE id = %s", (requisition_id,)).fetchone()
        if row is None:
            raise not_found("requisition")
        if row["active_version_id"] is None:
            raise ApiError(404, "no_approved_matrix", "This requisition has not been frozen yet.")
        return load_matrix(db, row["active_version_id"])


def _with_draft(
    auth: AuthContext,
    pool: Any,
    requisition_id: str,
    version_id: str,
    expected_revision: int,
    fn: Callable[[psycopg.Connection, str], T],
) -> T:
    """Locks the draft matrix and checks it is still editable at the caller's revision before ``fn`` runs."""
    requisition_id, version_id = require_id(requisition_id, "requisition"), require_id(version_id, "version")
    with with_tenant(pool, tenant_scope_of(auth)) as db:
        version = find_version(db, requisition_id, version_id, lock=True)
        matrix = db.execute(
            "SELECT id, status, matrix_revision FROM requisition.scoring_matrix WHERE jd_version_id = %s FOR UPDATE",
            (version_id,),
        ).fetchone()
        if matrix is None:
            raise matrix_not_found()
        if matrix["status"] == "Approved":
            raise ApiError(409, "matrix_approved", "An Approved scoring matrix is immutable.")
        if version["status"] not in OPEN_VERSION_STATES:
            raise ApiError(409, "version_closed", f"The JD version is {version['status']}; its matrix can no longer be edited.")
        if matrix["matrix_revision"] != expected_revision:
            # Another edit landed first (e.g. a second browser tab): reject and return the current state (TDD §8).
            current = load_matrix(db, version_id)
            raise ApiError(
                409,
                "revision_mismatch",
                "The matrix changed since you last read it; re-apply your edit to the current state.",
                current_matrix_revision=current["matrix_revision"],
                current_criteria=current["criteria"],
            )
        return fn(db, matrix["id"])


def find_version(db: psycopg.Connection, requisition_id: str, version_id: str, lock: bool) -> dict[str, Any]:
    if db.execute("SELECT 1 FROM requisition.job_requisition WHERE id = %s", (requisition_id,)).fetchone() is None:
        raise not_found("requisition")
    row = db.execute(
        "SELECT status FROM requisition.jd_version WHERE id = %s AND requisition_id = %s" + (" FOR UPDATE" if lock else ""),
        (version_id, requisition_id),
    ).fetchone()
    if row is None:
        raise not_found("version")
    return row


def bump_revision(db: psycopg.Connection, matrix_id: str, version_id: str) -> dict[str, Any]:
    db.execute("UPDATE requisition.scoring_matrix SET matrix_revision = matrix_revision + 1 WHERE id = %s", (matrix_id,))
    return load_matrix(db, version_id)


def load_matrix(db: psycopg.Connection, version_id: str) -> dict[str, Any]:
    """TDD §8 matrix representation, with the running total of the weights."""
    matrix = db.execute(
        "SELECT id, status, matrix_revision, approved_at FROM requisition.scoring_matrix WHERE jd_version_id = %s",
        (version_id,),
    ).fetchone()
    if matrix is None:
        raise matrix_not_found()
    rows = db.execute(
        """SELECT id, criterion_name, category, weight_percent, source_field_ref
             FROM requisition.scoring_criterion WHERE matrix_id = %s ORDER BY category, created_at, id""",
        (matrix["id"],),
    ).fetchall()
    criteria = [
        {
            "criterion_id": r["id"],
            "criterion_name": r["criterion_name"],
            "category": r["category"],
            "weight_percent": _number(r["weight_percent"]),
            "source_field_ref": r["source_field_ref"],
        }
        for r in rows
    ]
    # Exact decimal sum (numeric(5,2) in the database), so 33.33 + 33.33 + 33.34 is exactly 100.
    total = sum((Decimal(r["weight_percent"]) for r in rows), Decimal(0))
    return {
        "matrix_id": matrix["id"],
        "jd_version_id": version_id,
        "status": matrix["status"],
        "matrix_revision": matrix["matrix_revision"],
        "approved_at": matrix["approved_at"].isoformat() if matrix["approved_at"] else None,
        "criteria": criteria,
        "current_total_percent": _number(total),
    }


def _number(value: Decimal) -> int | float:
    """45.00 -> 45, 33.33 -> 33.33 (JSON numbers, as the API has always returned them)."""
    return int(value) if value == value.to_integral_value() else float(value)


def matrix_not_found() -> ApiError:
    return ApiError(404, "matrix_not_found", "This JD version has no scoring matrix.")
