"""Helpers shared by the requisition-service routers."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import Depends, Request
from psycopg_pool import ConnectionPool

from teamora_common import ApiError, AuthContext, TenantScope, is_uuid

Missing = Literal["requisition", "version", "criterion"]

_NOT_FOUND: dict[str, tuple[str, str]] = {
    "requisition": ("requisition_not_found", "No such requisition in your tenant."),
    "version": ("version_not_found", "No such JD version on this requisition."),
    "criterion": ("criterion_not_found", "No such criterion in this matrix."),
}


def not_found(what: Missing) -> ApiError:
    reason, message = _NOT_FOUND[what]
    return ApiError(404, reason, message)


def require_id(value: str, what: Missing) -> str:
    """A path id that isn't a UUID can't identify anything, so it is a 404 rather than a 422."""
    if not is_uuid(value):
        raise not_found(what)
    return value.lower()


def tenant_scope_of(auth: AuthContext) -> TenantScope:
    """The tenant scope for a request; a platform-admin token has none, so tenant APIs reject it (403)."""
    if auth.tenant_id is None:
        raise ApiError(
            403,
            "tenant_scope_required",
            "This API works within a tenant; a platform admin token has no tenant scope.",
        )
    return TenantScope(tenant_id=auth.tenant_id)


def require_role(auth: AuthContext, *roles: str) -> None:
    """403 unless the caller has one of ``roles`` (TDD §3.2 RBAC)."""
    if auth.role not in roles:
        raise ApiError(403, "role_not_allowed", f"This action needs one of these roles: {', '.join(roles)}.")


def get_pool(request: Request) -> ConnectionPool:
    return request.app.state.pool


#: Use as an endpoint parameter type: ``pool: Pool``.
Pool = Annotated[ConnectionPool, Depends(get_pool)]
