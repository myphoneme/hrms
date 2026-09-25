"""Teamora requisition-service (Module 1): port 3002, database role svc_requisition, schema `requisition`."""

from teamora_common import ServiceConfig, ServiceDefinition, create_app

SERVICE = ServiceDefinition(
    service_name="requisition-service",
    default_port=3002,
    db_role="svc_requisition",
    db_password_var="POSTGRES_SVC_REQUISITION_PASSWORD",
)


def build_app(config: ServiceConfig, pool=None):
    from . import freeze, intake, jd_versions, scoring_matrix

    return create_app(
        config,
        routers=[intake.router, jd_versions.router, scoring_matrix.router, freeze.router],
        pool=pool,
    )
