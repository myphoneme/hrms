"""Teamora auth-service: port 3001, database role svc_auth, schema `identity`."""

from teamora_common import ServiceConfig, ServiceDefinition, create_app

SERVICE = ServiceDefinition(
    service_name="auth-service",
    default_port=3001,
    db_role="svc_auth",
    db_password_var="POSTGRES_SVC_AUTH_PASSWORD",
)


def build_app(config: ServiceConfig, pool=None):
    return create_app(config, routers=[], pool=pool)
