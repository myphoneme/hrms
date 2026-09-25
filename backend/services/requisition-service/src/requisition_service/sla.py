"""HR-M1-FR-005 — approval SLA & escalation (BRD §4.1 step 6; TDD §12.1 step 7, §14, §16.5).

When a JD version is sent to the manager (PendingApproval), the database starts an SLA clock
(migration 0004). A scheduled check — never a user request — then records:

- a **reminder** for the manager once the tenant's reminder threshold has passed, and
- an **escalation** for the tenant's HR users once the escalation threshold has passed,

as long as the manager still hasn't responded. Thresholds are business days (Mon-Fri) in the tenant's
time zone. Events wait in ``approval_sla_event`` with ``delivery_status = pending`` for the Notification
Service (email / portal), which isn't built yet.

Run the check in-process (every ``SLA_CHECK_INTERVAL_SECONDS``, default 300; 0 turns it off) or once
from the command line: ``python -m requisition_service.sla [--env-file PATH]``.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import psycopg
from fastapi import APIRouter, Body, FastAPI
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, PlainValidator, WithJsonSchema, model_validator

from teamora_common import Auth, ConfigError, TenantScope, with_tenant

from .common import Pool, not_found, require_id, require_role, tenant_scope_of

logger = logging.getLogger("teamora.sla")

#: Defaults when a tenant hasn't configured its own policy (BRD example: 3 business days).
DEFAULT_POLICY = {"reminder_after_business_days": 3, "escalate_after_business_days": 5, "timezone": "Asia/Kolkata"}
DEFAULT_INTERVAL_SECONDS = 300
BATCH_SIZE = 200


# --- business days ------------------------------------------------------------------------------------


def add_business_days(start: datetime, days: int, timezone: str) -> datetime:
    """``start`` plus ``days`` business days (Mon-Fri) in ``timezone``, same local time of day.

    Friday 16:00 + 3 business days = Wednesday 16:00; Saturday 10:00 + 1 = Monday 10:00.
    Public holidays are not counted in Release 1.
    """
    local = start.astimezone(ZoneInfo(timezone))
    remaining = days
    while remaining > 0:
        local += timedelta(days=1)
        if local.weekday() < 5:
            remaining -= 1
    # Aware-datetime arithmetic keeps the local wall time; the zone supplies the offset for the new date.
    return local.astimezone(UTC)


# --- policy -------------------------------------------------------------------------------------------


def _timezone(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("must be an IANA time zone name, e.g. Asia/Kolkata")
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("must be an IANA time zone name, e.g. Asia/Kolkata") from exc
    return value


def _days(low: int, high: int):
    def check(value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise ValueError(f"must be a whole number of business days from {low} to {high}")
        return value

    return Annotated[int, PlainValidator(check), WithJsonSchema({"type": "integer", "minimum": low, "maximum": high})]


class PolicyRequest(BaseModel):
    reminder_after_business_days: _days(1, 20)
    escalate_after_business_days: _days(2, 30)
    timezone: Annotated[str, PlainValidator(_timezone), WithJsonSchema({"type": "string", "example": "Asia/Kolkata"})] = (
        DEFAULT_POLICY["timezone"]
    )

    @model_validator(mode="after")
    def _escalation_after_reminder(self) -> PolicyRequest:
        if self.escalate_after_business_days <= self.reminder_after_business_days:
            raise ValueError("escalate_after_business_days must be greater than reminder_after_business_days")
        return self


def load_policy(db: psycopg.Connection) -> dict[str, Any]:
    """The caller's tenant policy (``with_tenant`` scope), or the defaults."""
    row = db.execute(
        "SELECT reminder_after_business_days, escalate_after_business_days, timezone, updated_at FROM requisition.sla_policy"
    ).fetchone()
    if row is None:
        return {**DEFAULT_POLICY, "is_default": True, "updated_at": None}
    return {**row, "is_default": False, "updated_at": _iso(row["updated_at"])}


# --- API ----------------------------------------------------------------------------------------------

router = APIRouter(tags=["HR-M1-FR-005 · Approval SLA"])


@router.get("/sla-policy", summary="The tenant's approval SLA (reminder / escalation after N business days)")
def get_policy(auth: Auth, pool: Pool) -> dict[str, Any]:
    with with_tenant(pool, tenant_scope_of(auth)) as db:
        return load_policy(db)


@router.put("/sla-policy", summary="Set the tenant's approval SLA (tenant_admin only)")
def put_policy(
    body: Annotated[
        PolicyRequest,
        Body(
            openapi_examples={
                "default": {
                    "value": {"reminder_after_business_days": 3, "escalate_after_business_days": 5, "timezone": "Asia/Kolkata"}
                }
            }
        ),
    ],
    auth: Auth,
    pool: Pool,
) -> dict[str, Any]:
    scope = tenant_scope_of(auth)
    require_role(auth, "tenant_admin")
    with with_tenant(pool, scope) as db:
        db.execute(
            """INSERT INTO requisition.sla_policy
                 (tenant_id, reminder_after_business_days, escalate_after_business_days, timezone, updated_by)
               VALUES (%(t)s, %(r)s, %(e)s, %(tz)s, %(u)s)
               ON CONFLICT (tenant_id) DO UPDATE
                 SET reminder_after_business_days = EXCLUDED.reminder_after_business_days,
                     escalate_after_business_days = EXCLUDED.escalate_after_business_days,
                     timezone = EXCLUDED.timezone, updated_by = EXCLUDED.updated_by, updated_at = now()""",
            {
                "t": scope.tenant_id,
                "r": body.reminder_after_business_days,
                "e": body.escalate_after_business_days,
                "tz": body.timezone,
                "u": auth.user_id,
            },
        )
        return load_policy(db)


@router.get(
    "/requisitions/{requisition_id}/sla", summary="SLA state of a requisition's pending approval, with its reminders/escalations"
)
def get_requisition_sla(requisition_id: str, auth: Auth, pool: Pool) -> dict[str, Any]:
    requisition_id = require_id(requisition_id, "requisition")
    with with_tenant(pool, tenant_scope_of(auth)) as db:
        if db.execute("SELECT 1 FROM requisition.job_requisition WHERE id = %s", (requisition_id,)).fetchone() is None:
            raise not_found("requisition")
        policy = load_policy(db)
        clock = db.execute(
            """SELECT id, jd_version_id, pending_since, reminded_at, escalated_at, resolved_at, resolution
                 FROM requisition.approval_sla_clock WHERE requisition_id = %s
                ORDER BY pending_since DESC, id DESC LIMIT 1""",
            (requisition_id,),
        ).fetchone()
        events = db.execute(
            f"SELECT {EVENT_COLUMNS} FROM requisition.approval_sla_event WHERE requisition_id = %s ORDER BY created_at, kind",
            (requisition_id,),
        ).fetchall()
    return {"policy": policy, "clock": _clock_dto(clock, policy), "events": [_event_dto(e) for e in events]}


@router.get("/sla-events", summary="Reminders and escalations (HR: all in the tenant; a manager: their own reminders)")
def list_events(
    auth: Auth,
    pool: Pool,
    kind: Literal["reminder", "escalation"] | None = None,
    delivery_status: Literal["pending", "sent", "failed"] | None = None,
) -> list[dict[str, Any]]:
    scope = tenant_scope_of(auth)
    conditions, params = [], []
    if kind:
        conditions.append("kind = %s")
        params.append(kind)
    if delivery_status:
        conditions.append("delivery_status = %s")
        params.append(delivery_status)
    if auth.role not in ("recruiter_hr", "tenant_admin"):
        conditions.append("recipient_user_id = %s")
        params.append(auth.user_id)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with with_tenant(pool, scope) as db:
        rows = db.execute(
            f"SELECT {EVENT_COLUMNS} FROM requisition.approval_sla_event {where} ORDER BY created_at DESC LIMIT 200",
            params,
        ).fetchall()
    return [_event_dto(r) for r in rows]


EVENT_COLUMNS = """id, requisition_id, jd_version_id, kind, recipient_role, recipient_user_id, due_at,
  created_at, delivery_status, delivered_at"""


def _iso(value: datetime | None) -> str | None:
    """Always UTC, so every timestamp in an SLA response is directly comparable."""
    return value.astimezone(UTC).isoformat() if value else None


def _event_dto(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "due_at": _iso(row["due_at"]),
        "created_at": _iso(row["created_at"]),
        "delivered_at": _iso(row["delivered_at"]),
    }


def _clock_dto(clock: dict[str, Any] | None, policy: dict[str, Any]) -> dict[str, Any] | None:
    if clock is None:
        return None
    reminder_due, escalation_due = due_times(clock["pending_since"], policy)
    return {
        "jd_version_id": clock["jd_version_id"],
        "status": "open" if clock["resolved_at"] is None else "resolved",
        "pending_since": _iso(clock["pending_since"]),
        "reminder_due_at": _iso(reminder_due),
        "escalation_due_at": _iso(escalation_due),
        "reminded_at": _iso(clock["reminded_at"]),
        "escalated_at": _iso(clock["escalated_at"]),
        "resolved_at": _iso(clock["resolved_at"]),
        "resolution": clock["resolution"],
    }


def due_times(pending_since: datetime, policy: dict[str, Any]) -> tuple[datetime, datetime]:
    tz = policy["timezone"]
    return (
        add_business_days(pending_since, policy["reminder_after_business_days"], tz),
        add_business_days(pending_since, policy["escalate_after_business_days"], tz),
    )


# --- the scheduled check ------------------------------------------------------------------------------


def run_sla_check(pool: ConnectionPool, now: datetime | None = None) -> dict[str, int]:
    """One pass over the open SLA clocks of every tenant; returns what it did.

    Safe to run concurrently (several replicas, or the CLI while the service runs): each clock is
    locked with SKIP LOCKED while processed, and each reminder/escalation is unique per clock.
    """
    now = now or datetime.now(UTC)
    summary = {"checked": 0, "reminders": 0, "escalations": 0, "resolved": 0}
    with pool.connection() as conn:
        # Cross-tenant on purpose: the clock table holds only ids and timestamps (see migration 0004).
        due = conn.execute(
            """SELECT id, tenant_id FROM requisition.approval_sla_clock
                WHERE resolved_at IS NULL AND (reminded_at IS NULL OR escalated_at IS NULL)
                ORDER BY pending_since LIMIT %s""",
            (BATCH_SIZE,),
        ).fetchall()
    for clock in due:
        try:
            result = _check_clock(pool, clock["id"], clock["tenant_id"], now)
        except Exception:  # noqa: BLE001 - one bad clock must not stop the others
            logger.exception("SLA check failed for clock %s", clock["id"])
            continue
        summary["checked"] += 1
        for key in ("reminders", "escalations", "resolved"):
            summary[key] += result.get(key, 0)
    return summary


def _check_clock(pool: ConnectionPool, clock_id: str, tenant_id: str, now: datetime) -> dict[str, int]:
    done: dict[str, int] = {}
    with with_tenant(pool, TenantScope(tenant_id)) as db:
        clock = db.execute(
            """SELECT id, requisition_id, jd_version_id, pending_since, reminded_at, escalated_at
                 FROM requisition.approval_sla_clock WHERE id = %s AND resolved_at IS NULL FOR UPDATE SKIP LOCKED""",
            (clock_id,),
        ).fetchone()
        if clock is None:  # resolved meanwhile, or another check holds it
            return done
        # Re-read under RLS: the clock's own tenant scope must show the version and requisition.
        state = db.execute(
            """SELECT v.status AS version_status, r.status AS requisition_status, r.created_by
                 FROM requisition.jd_version v JOIN requisition.job_requisition r ON r.id = v.requisition_id
                WHERE v.id = %s""",
            (clock["jd_version_id"],),
        ).fetchone()
        if state is None or state["version_status"] != "PendingApproval" or state["requisition_status"] in ("OnHold", "Closed"):
            # Normally the triggers resolve clocks; this only catches anything they couldn't see.
            resolution = (
                "stale"
                if state is None
                else (
                    state["requisition_status"]
                    if state["requisition_status"] in ("OnHold", "Closed")
                    else state["version_status"]
                )
            )
            db.execute(
                "UPDATE requisition.approval_sla_clock SET resolved_at = now(), resolution = %s WHERE id = %s",
                (resolution, clock_id),
            )
            done["resolved"] = 1
            return done

        reminder_due, escalation_due = due_times(clock["pending_since"], load_policy(db))
        event = """INSERT INTO requisition.approval_sla_event
                     (clock_id, tenant_id, requisition_id, jd_version_id, kind, recipient_role, recipient_user_id, due_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (clock_id, kind) DO NOTHING"""
        ids = (clock_id, tenant_id, clock["requisition_id"], clock["jd_version_id"])
        if clock["reminded_at"] is None and now >= reminder_due:
            db.execute(event, (*ids, "reminder", "manager", state["created_by"], reminder_due))
            db.execute("UPDATE requisition.approval_sla_clock SET reminded_at = %s WHERE id = %s", (now, clock_id))
            done["reminders"] = 1
        if clock["escalated_at"] is None and now >= escalation_due:
            db.execute(event, (*ids, "escalation", "recruiter_hr", None, escalation_due))
            db.execute("UPDATE requisition.approval_sla_clock SET escalated_at = %s WHERE id = %s", (now, clock_id))
            done["escalations"] = 1
    return done


def interval_from_env(env: dict[str, str] | None = None) -> float:
    raw = (os.environ if env is None else env).get("SLA_CHECK_INTERVAL_SECONDS", "").strip()
    if not raw:
        return DEFAULT_INTERVAL_SECONDS
    try:
        value = float(raw)
    except ValueError:
        value = -1
    if value < 0:
        raise ConfigError(f'SLA_CHECK_INTERVAL_SECONDS must be a number of seconds, 0 to turn the check off (got "{raw}")')
    return value


def sla_worker(interval_seconds: float):
    """A background worker for ``create_app``: runs the check every ``interval_seconds`` until stopped."""

    def sla_check_loop(app: FastAPI, stop: threading.Event) -> None:
        logger.info("SLA check every %ss", interval_seconds)
        while not stop.wait(interval_seconds):
            try:
                summary = run_sla_check(app.state.pool)
                if summary["reminders"] or summary["escalations"] or summary["resolved"]:
                    logger.info("SLA check: %s", summary)
            except Exception:  # noqa: BLE001 - keep checking; the database may be briefly unavailable
                logger.exception("SLA check failed")

    return sla_check_loop


def main() -> None:
    """``python -m requisition_service.sla [--env-file PATH]`` — one check, e.g. from a scheduled task."""
    from teamora_common import create_pool, load_service_config
    from teamora_common.env_file import apply_env_file_arg

    from . import SERVICE

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    apply_env_file_arg(sys.argv[1:])
    try:
        config = load_service_config(SERVICE)
    except ConfigError as exc:
        sys.exit(str(exc))
    pool = create_pool(config)
    pool.open(wait=True, timeout=10)
    try:
        print(run_sla_check(pool))
    finally:
        pool.close()


if __name__ == "__main__":
    main()
