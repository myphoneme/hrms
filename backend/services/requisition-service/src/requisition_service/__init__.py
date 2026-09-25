"""Teamora requisition-service (Module 1): port 3002, database role svc_requisition, schema `requisition`."""

from teamora_common import ServiceConfig, ServiceDefinition, create_app

SERVICE = ServiceDefinition(
    service_name="requisition-service",
    default_port=3002,
    db_role="svc_requisition",
    db_password_var="POSTGRES_SVC_REQUISITION_PASSWORD",
)


def build_app(config: ServiceConfig, pool=None, sla_interval_seconds: float | None = None):
    """``sla_interval_seconds``: how often the approval SLA check runs in-process (0 = off). Defaults to
    SLA_CHECK_INTERVAL_SECONDS (300) with the real pool, and to off when a test passes its own pool."""
    from . import freeze, intake, jd_versions, scoring_matrix, sla

    if sla_interval_seconds is None:
        sla_interval_seconds = sla.interval_from_env() if pool is None else 0
    return create_app(
        config,
        routers=[intake.router, jd_versions.router, scoring_matrix.router, freeze.router, sla.router],
        pool=pool,
        workers=[sla.sla_worker(sla_interval_seconds)] if sla_interval_seconds > 0 else [],
    )
