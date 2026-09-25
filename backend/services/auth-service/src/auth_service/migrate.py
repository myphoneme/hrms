"""python -m auth_service.migrate [--env-file PATH] — applies the `identity` schema migrations."""

from teamora_common import migrations_cli

if __name__ == "__main__":
    migrations_cli("identity", "auth_service")
