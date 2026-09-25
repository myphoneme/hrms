"""Prints an access token for a demo manager, for manual API checks (API page "Authorize", requests.http).

Usage (from backend/, with the venv active):
    python dev/make_token.py                 -> Demo Staffing Agency manager, valid 8 hours
    python dev/make_token.py employer        -> Demo Direct Employer manager
    python dev/make_token.py agency 2        -> valid 2 hours
"""

import os
import sys

from demo import ENV_FILE, TENANTS, USERS

from teamora_common import AuthContext, load_env_file, sign_access_token


def main() -> None:
    if ENV_FILE.exists():
        load_env_file(ENV_FILE)
    who = sys.argv[1] if len(sys.argv) > 1 else "agency"
    hours = float(sys.argv[2]) if len(sys.argv) > 2 else 8

    if os.environ.get("APP_ENV") not in ("local", "test"):
        sys.exit(f"Refusing: dev tokens are for APP_ENV=local/test only (APP_ENV={os.environ.get('APP_ENV')}).")
    if who not in USERS:
        sys.exit(f'Unknown demo user "{who}". Use one of: {", ".join(USERS)}')
    secret = os.environ.get("AUTH_JWT_SECRET")
    if not secret:
        sys.exit("AUTH_JWT_SECRET is not set (backend/.env).")

    user = USERS[who]
    tenant = TENANTS[user["tenant"]]
    token = sign_access_token(
        secret, AuthContext(user_id=user["id"], tenant_id=tenant["id"], role=user["role"]), round(hours * 3600)
    )
    print(f"# {user['email']} ({tenant['name']}), valid {hours:g} h", file=sys.stderr)
    print(token)


if __name__ == "__main__":
    main()
