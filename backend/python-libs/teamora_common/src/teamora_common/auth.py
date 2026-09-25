"""Access tokens (TDD §3): HS256 JWTs issued by auth-service and verified by every service."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Annotated, Literal

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .db import is_uuid
from .errors import ApiError

UserRole = Literal["platform_admin", "tenant_admin", "manager", "recruiter_hr"]
USER_ROLES: tuple[str, ...] = ("platform_admin", "tenant_admin", "manager", "recruiter_hr")

ISSUER = "teamora-auth"
AUDIENCE = "teamora"
ACCESS_TOKEN_TTL_SECONDS = 15 * 60  # TDD §3.3: short-lived 15-minute access tokens


@dataclass(frozen=True)
class AuthContext:
    """Who is calling, as proven by a verified access token."""

    user_id: str
    #: None only for a Phoneme Platform Admin, who is not scoped to any tenant.
    tenant_id: str | None
    role: UserRole


class InvalidTokenError(Exception):
    pass


def sign_access_token(secret: str, auth: AuthContext, ttl_seconds: int = ACCESS_TOKEN_TTL_SECONDS) -> str:
    """Issues an access token. Used by auth-service at login, and by tests and the dev kit."""
    now = int(time.time())
    claims = {
        "sub": auth.user_id,
        "tenant_id": auth.tenant_id,
        "role": auth.role,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return jwt.encode(claims, secret, algorithm="HS256")


def verify_access_token(secret: str, token: str) -> AuthContext:
    """Verifies signature, issuer, audience and expiry, then the claim shapes. Raises InvalidTokenError."""
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("token expired") from exc
    except jwt.InvalidAudienceError as exc:
        raise InvalidTokenError("invalid audience") from exc
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    sub, tenant_id, role = payload.get("sub"), payload.get("tenant_id"), payload.get("role")
    if not is_uuid(sub):
        raise InvalidTokenError("invalid sub claim")
    if role not in USER_ROLES:
        raise InvalidTokenError("invalid role claim")
    if (tenant_id is not None) if role == "platform_admin" else not is_uuid(tenant_id):
        raise InvalidTokenError("invalid tenant_id claim")
    return AuthContext(user_id=sub, tenant_id=tenant_id, role=role)


# auto_error=False: we answer missing/invalid tokens with our own error body. The scheme also gives
# the API docs page its "Authorize" button.
_bearer = HTTPBearer(auto_error=False, description="Access token (local: `python dev/make_token.py`)")


def require_auth(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthContext:
    """Dependency: rejects any request without a valid ``Authorization: Bearer <access token>`` with 401."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError(401, "missing_token", "A Bearer access token is required.")
    try:
        return verify_access_token(request.app.state.config.auth_jwt_secret, credentials.credentials.strip())
    except InvalidTokenError as exc:
        raise ApiError(401, "invalid_token", "The access token is invalid or expired.") from exc


#: Use as an endpoint parameter type: ``auth: Auth``.
Auth = Annotated[AuthContext, Depends(require_auth)]
