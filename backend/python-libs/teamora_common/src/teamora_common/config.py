"""Service configuration from environment variables.

The variable names are the same in every environment: a local backend/.env on developer machines,
Coolify variables on staging/production (Technical Stack Charter, "Database rules").
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

AppEnv = Literal["local", "test", "staging", "production"]
APP_ENVS: tuple[str, ...] = ("local", "test", "staging", "production")

#: Same database name in every environment; only credentials change (Charter, Database rules 3).
DATABASE_NAME = "teamora"

#: Login role that owns every schema and is the only role that runs migrations (backend/db/init).
MIGRATOR_ROLE = "teamora_migrator"

MIN_JWT_SECRET_LENGTH = 32


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str


@dataclass(frozen=True)
class ServiceConfig:
    service_name: str
    app_env: AppEnv
    port: int
    db: DatabaseConfig
    #: HS256 key used to verify access tokens (TDD §3.3); at least 32 characters.
    auth_jwt_secret: str


@dataclass(frozen=True)
class ServiceDefinition:
    service_name: str
    default_port: int
    #: Login role created by backend/db/init, e.g. ``svc_auth``.
    db_role: str
    #: Environment variable holding that role's password, e.g. ``POSTGRES_SVC_AUTH_PASSWORD``.
    db_password_var: str


class ConfigError(Exception):
    pass


def load_service_config(definition: ServiceDefinition, env: Mapping[str, str] | None = None) -> ServiceConfig:
    """Reads and validates a service's configuration.

    Collects every problem before failing, so a misconfigured deploy reports all of them at once.
    """
    env = os.environ if env is None else env
    problems: list[str] = []
    required = _required_reader(env, problems)

    app_env = _read_app_env(required, problems)
    db = _read_database(env, required, problems, definition.db_role, definition.db_password_var)
    secret = required("AUTH_JWT_SECRET")
    if secret and len(secret) < MIN_JWT_SECRET_LENGTH:
        problems.append(f"AUTH_JWT_SECRET must be at least {MIN_JWT_SECRET_LENGTH} characters")
    port = _parse_port("PORT", env.get("PORT"), definition.default_port, problems)

    if problems:
        raise ConfigError(_format(definition.service_name, problems))
    return ServiceConfig(
        service_name=definition.service_name,
        app_env=app_env,  # type: ignore[arg-type]
        port=port,
        db=db,
        auth_jwt_secret=secret,
    )


def load_migrator_config(env: Mapping[str, str] | None = None) -> DatabaseConfig:
    """Connection settings for running migrations as teamora_migrator (never used by a running service)."""
    env = os.environ if env is None else env
    problems: list[str] = []
    required = _required_reader(env, problems)
    _read_app_env(required, problems)
    db = _read_database(env, required, problems, MIGRATOR_ROLE, "POSTGRES_MIGRATOR_PASSWORD")
    if problems:
        raise ConfigError(_format("migrations", problems))
    return db


def _format(who: str, problems: list[str]) -> str:
    return f"{who}: invalid configuration:\n  - " + "\n  - ".join(problems)


def _required_reader(env: Mapping[str, str], problems: list[str]):
    def required(name: str) -> str:
        value = (env.get(name) or "").strip()
        if not value:
            problems.append(f"{name} is not set")
        return value

    return required


def _read_app_env(required, problems: list[str]) -> str:
    app_env = required("APP_ENV")
    if app_env and app_env not in APP_ENVS:
        problems.append(f'APP_ENV must be one of {", ".join(APP_ENVS)} (got "{app_env}")')
    return app_env


def _read_database(env: Mapping[str, str], required, problems: list[str], user: str, password_var: str) -> DatabaseConfig:
    host = required("POSTGRES_HOST")
    password = required(password_var)
    database = (env.get("POSTGRES_DB") or "").strip() or DATABASE_NAME
    if database != DATABASE_NAME:
        problems.append(f'POSTGRES_DB must be "{DATABASE_NAME}" in every environment (got "{database}")')
    port = _parse_port("POSTGRES_PORT", env.get("POSTGRES_PORT"), 5432, problems)
    return DatabaseConfig(host=host, port=port, database=database, user=user, password=password)


def _parse_port(name: str, raw: str | None, fallback: int, problems: list[str]) -> int:
    if raw is None or raw.strip() == "":
        return fallback
    try:
        value = int(raw.strip())
    except ValueError:
        value = -1
    if not 1 <= value <= 65535:
        problems.append(f'{name} must be a port number (got "{raw}")')
        return fallback
    return value
