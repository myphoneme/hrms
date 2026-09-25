"""Plain-SQL migrations, one schema per service."""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from importlib.resources import files
from importlib.resources.abc import Traversable

import psycopg

from .config import ConfigError, DatabaseConfig, load_migrator_config
from .env_file import apply_env_file_arg

_MIGRATION_FILE = re.compile(r"^\d{4}_[a-z0-9_]+\.sql$")
_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")


def run_migrations(
    schema: str,
    migrations: Traversable,
    connection: DatabaseConfig,
    log: Callable[[str], None] = lambda _: None,
) -> list[str]:
    """Applies pending ``NNNN_description.sql`` files for one service schema, in file-name order.

    Each file runs in its own transaction and is recorded in ``<schema>.schema_migrations``. Runs as
    teamora_migrator, so every table is owned by it and service roles never own (and so never bypass
    Row-Level Security on) a table. A per-schema advisory lock makes concurrent runs (two deploys at
    once) safe.
    """
    if not _IDENTIFIER.match(schema):
        raise ValueError(f'invalid schema name "{schema}"')
    table = f'"{schema}".schema_migrations'
    names = sorted(f.name for f in migrations.iterdir() if _MIGRATION_FILE.match(f.name))

    with psycopg.connect(
        host=connection.host,
        port=connection.port,
        dbname=connection.database,
        user=connection.user,
        password=connection.password,
        application_name=f"migrate:{schema}",
        autocommit=True,
    ) as conn:
        conn.execute("SELECT pg_advisory_lock(hashtext(%s))", (f"teamora-migrate:{schema}",))
        try:
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {table} (version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            # Default privileges grant service roles DML on new tables; the migration history is migrator-only.
            grantees = conn.execute(
                """SELECT DISTINCT grantee FROM information_schema.role_table_grants
                    WHERE table_schema = %s AND table_name = 'schema_migrations' AND grantee <> current_user""",
                (schema,),
            ).fetchall()
            for (grantee,) in grantees:
                if grantee == "PUBLIC":
                    conn.execute(f"REVOKE ALL ON {table} FROM PUBLIC")
                elif _IDENTIFIER.match(grantee):
                    conn.execute(f'REVOKE ALL ON {table} FROM "{grantee}"')

            applied = {row[0] for row in conn.execute(f"SELECT version FROM {table}")}
            done: list[str] = []
            for name in names:
                version = name.removesuffix(".sql")
                if version in applied:
                    continue
                sql = migrations.joinpath(name).read_text(encoding="utf-8")
                try:
                    with conn.transaction():
                        # No parameters, so the whole file runs as one multi-statement script.
                        conn.execute(sql)  # type: ignore[arg-type]
                        conn.execute(f"INSERT INTO {table} (version) VALUES (%s)", (version,))
                except psycopg.Error as exc:
                    raise RuntimeError(f"migration {schema}/{name} failed: {exc}") from exc
                log(f"applied {schema}/{name}")
                done.append(version)
            if not done:
                log(f"{schema}: up to date ({len(names)} migration(s))")
            return done
        finally:
            conn.execute("SELECT pg_advisory_unlock_all()")


def migrations_cli(schema: str, package: str) -> None:
    """Entry point for ``python -m <service>.migrate [--env-file PATH]``.

    Migration files ship inside the service package, in ``<package>/migrations/``.
    """
    apply_env_file_arg(sys.argv[1:])
    try:
        run_migrations(schema, files(package).joinpath("migrations"), load_migrator_config(), log=print)
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001 - one clear line for a failed deploy step
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
