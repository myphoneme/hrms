import time

import jwt
import pytest

from teamora_common import AuthContext, InvalidTokenError, sign_access_token, verify_access_token

SECRET = "unit-test-secret-unit-test-secret-0001"
MANAGER = AuthContext(
    user_id="0190a1b2-0000-7000-8000-000000000001", tenant_id="0190a1b2-0000-7000-8000-00000000000a", role="manager"
)


def _raw(claims: dict, key: str = SECRET, algorithm: str = "HS256") -> str:
    base = {"sub": MANAGER.user_id, "iss": "teamora-auth", "aud": "teamora", "exp": int(time.time()) + 60}
    return jwt.encode({**base, **claims}, key, algorithm=algorithm)


def test_round_trips_a_tenant_user():
    assert verify_access_token(SECRET, sign_access_token(SECRET, MANAGER)) == MANAGER


def test_allows_a_platform_admin_with_no_tenant():
    admin = AuthContext(user_id=MANAGER.user_id, tenant_id=None, role="platform_admin")
    assert verify_access_token(SECRET, sign_access_token(SECRET, admin)) == admin


def test_rejects_a_token_signed_with_another_secret():
    token = sign_access_token("another-secret-another-secret-0000001", MANAGER)
    with pytest.raises(InvalidTokenError):
        verify_access_token(SECRET, token)


def test_rejects_an_expired_token():
    with pytest.raises(InvalidTokenError, match="expired"):
        verify_access_token(SECRET, sign_access_token(SECRET, MANAGER, ttl_seconds=-10))


def test_rejects_a_tenant_user_without_tenant_id_and_an_admin_with_one():
    with pytest.raises(InvalidTokenError, match="tenant_id"):
        verify_access_token(SECRET, _raw({"tenant_id": None, "role": "manager"}))
    with pytest.raises(InvalidTokenError, match="tenant_id"):
        verify_access_token(SECRET, _raw({"tenant_id": MANAGER.tenant_id, "role": "platform_admin"}))


def test_rejects_an_unknown_role_and_a_wrong_audience():
    with pytest.raises(InvalidTokenError, match="role"):
        verify_access_token(SECRET, _raw({"tenant_id": MANAGER.tenant_id, "role": "superuser"}))
    with pytest.raises(InvalidTokenError, match="audience"):
        verify_access_token(SECRET, _raw({"tenant_id": MANAGER.tenant_id, "role": "manager", "aud": "someone-else"}))


def test_rejects_the_none_algorithm():
    unsigned = jwt.encode(
        {"sub": MANAGER.user_id, "tenant_id": MANAGER.tenant_id, "role": "manager", "iss": "teamora-auth", "aud": "teamora"},
        None,
        algorithm="none",
    )
    with pytest.raises(InvalidTokenError):
        verify_access_token(SECRET, unsigned)
