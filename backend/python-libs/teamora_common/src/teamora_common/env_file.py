"""Loads a local ``.env`` file into the environment (local development only).

Same rules as backend/db/bootstrap.sh: ``NAME=value`` lines, ``#`` comments, optional surrounding
quotes, and values already set in the environment win. Staging/production get their variables from
Coolify and never use a file.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: str | Path) -> None:
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = (part.strip() for part in line.split("=", 1))
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if name and not os.environ.get(name):
            os.environ[name] = value


def apply_env_file_arg(argv: list[str]) -> None:
    """Handles an optional ``--env-file PATH`` command-line argument."""
    if "--env-file" in argv:
        index = argv.index("--env-file")
        if index + 1 >= len(argv):
            raise SystemExit("--env-file needs a path")
        load_env_file(argv[index + 1])
