"""python -m requisition_service.migrate [--env-file PATH] — applies the `requisition` schema migrations.

Run after auth_service.migrate: requisition tables reference `identity` (tenants, clients).
"""

from teamora_common import migrations_cli

if __name__ == "__main__":
    migrations_cli("requisition", "requisition_service")
