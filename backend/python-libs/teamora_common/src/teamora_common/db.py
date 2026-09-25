"""Database access: one connection pool per service, and tenant-scoped transactions (TDD §5.3)."""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row
from psycopg.types.string import TextLoader
from psycopg_pool import ConnectionPool

from .config import ServiceConfig

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


def is_uuid(value: object) -> bool:
    return isinstance(value, str) and bool(_UUID.match(value))


def _configure(conn: psycopg.Connection) -> None:
    # UUIDs come back as plain strings, exactly as the API sends and receives them.
    conn.adapters.register_loader("uuid", TextLoader)


def create_pool(config: ServiceConfig) -> ConnectionPool:
    """A pool logged in as the service's own role (e.g. svc_auth), which can only reach its own schema.

    Never the superuser or teamora_migrator. Opened by the app on startup, without waiting for the
    database, so the service starts (and reports /health/ready = 503) even if the database is down.
    """
    db = config.db
    return ConnectionPool(
        kwargs={
            "host": db.host,
            "port": db.port,
            "dbname": db.database,
            "user": db.user,
            "password": db.password,
            "application_name": config.service_name,
            "connect_timeout": 5,
            "row_factory": dict_row,
        },
        min_size=1,
        max_size=10,
        timeout=5,
        configure=_configure,
        name=config.service_name,
        open=False,
    )


@dataclass(frozen=True)
class TenantScope:
    """The (tenant, client) scope every multi-tenant query runs under (TDD §5.2)."""

    tenant_id: str
    #: None for a direct-employer tenant or when a request is not client-scoped.
    client_id: str | None = None


@contextmanager
def with_tenant(pool: ConnectionPool, scope: TenantScope) -> Iterator[psycopg.Connection]:
    """One transaction with the tenant scope set as transaction-local settings.

    Every multi-tenant table's Row-Level Security policy reads ``app.tenant_id`` / ``app.client_id``;
    a connection without them sees zero rows (TDD §5.3). This is the only way service code should
    query multi-tenant tables. Any exception inside the block rolls the transaction back.
    """
    if not is_uuid(scope.tenant_id):
        raise ValueError("with_tenant: tenant_id must be a UUID")
    if scope.client_id is not None and not is_uuid(scope.client_id):
        raise ValueError("with_tenant: client_id must be a UUID or None")

    with pool.connection() as conn, conn.transaction():
        conn.execute(
            "SELECT set_config('app.tenant_id', %s, true), set_config('app.client_id', %s, true)",
            (scope.tenant_id, scope.client_id or ""),
        )
        yield conn
