"""Shared foundation for Teamora FastAPI services."""

from .app import API_DOCS_PATH, API_PREFIX, create_app, run_service
from .auth import (
    USER_ROLES,
    Auth,
    AuthContext,
    InvalidTokenError,
    UserRole,
    require_auth,
    sign_access_token,
    verify_access_token,
)
from .config import (
    DATABASE_NAME,
    MIGRATOR_ROLE,
    ConfigError,
    DatabaseConfig,
    ServiceConfig,
    ServiceDefinition,
    load_migrator_config,
    load_service_config,
)
from .db import TenantScope, create_pool, is_uuid, with_tenant
from .env_file import load_env_file
from .errors import MISSING_FIELD_HINTS, ApiError, unprocessable
from .migrations import migrations_cli, run_migrations

__all__ = [
    "API_DOCS_PATH",
    "API_PREFIX",
    "DATABASE_NAME",
    "MIGRATOR_ROLE",
    "MISSING_FIELD_HINTS",
    "USER_ROLES",
    "ApiError",
    "Auth",
    "AuthContext",
    "ConfigError",
    "DatabaseConfig",
    "InvalidTokenError",
    "ServiceConfig",
    "ServiceDefinition",
    "TenantScope",
    "UserRole",
    "create_app",
    "create_pool",
    "is_uuid",
    "load_env_file",
    "load_migrator_config",
    "load_service_config",
    "migrations_cli",
    "require_auth",
    "run_migrations",
    "run_service",
    "sign_access_token",
    "unprocessable",
    "verify_access_token",
    "with_tenant",
]
