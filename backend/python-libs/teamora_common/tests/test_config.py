import pytest

from teamora_common import ConfigError, ServiceDefinition, load_migrator_config, load_service_config

DEF = ServiceDefinition(
    service_name="auth-service", default_port=3001, db_role="svc_auth", db_password_var="POSTGRES_SVC_AUTH_PASSWORD"
)

VALID = {
    "APP_ENV": "local",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_SVC_AUTH_PASSWORD": "local-password-123",
    "AUTH_JWT_SECRET": "local-jwt-secret-local-jwt-secret-0001",
}


def test_builds_config_logging_in_as_the_service_role():
    config = load_service_config(DEF, dict(VALID))
    assert config.service_name == "auth-service"
    assert config.app_env == "local"
    assert config.port == 3001
    assert (config.db.host, config.db.port, config.db.database) == ("localhost", 5432, "teamora")
    assert (config.db.user, config.db.password) == ("svc_auth", "local-password-123")
    assert config.auth_jwt_secret == "local-jwt-secret-local-jwt-secret-0001"


def test_uses_port_and_postgres_port_when_set():
    config = load_service_config(DEF, {**VALID, "PORT": "4001", "POSTGRES_PORT": "5433"})
    assert config.port == 4001
    assert config.db.port == 5433


def test_reports_every_missing_variable_at_once():
    with pytest.raises(ConfigError) as exc:
        load_service_config(DEF, {})
    for name in ("APP_ENV", "POSTGRES_HOST", "POSTGRES_SVC_AUTH_PASSWORD", "AUTH_JWT_SECRET"):
        assert f"{name} is not set" in str(exc.value)


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"APP_ENV": "dev"}, "APP_ENV must be one of"),
        ({"POSTGRES_DB": "teamora_dev"}, 'POSTGRES_DB must be "teamora"'),
        ({"PORT": "abc"}, "PORT must be a port number"),
        ({"AUTH_JWT_SECRET": "too-short"}, "AUTH_JWT_SECRET must be at least 32 characters"),
    ],
)
def test_rejects_invalid_values(override, message):
    with pytest.raises(ConfigError, match=message):
        load_service_config(DEF, {**VALID, **override})


def test_migrator_logs_in_as_teamora_migrator():
    db = load_migrator_config({"APP_ENV": "local", "POSTGRES_HOST": "localhost", "POSTGRES_MIGRATOR_PASSWORD": "migrator-pw-123"})
    assert (db.user, db.password, db.database) == ("teamora_migrator", "migrator-pw-123", "teamora")


def test_migrator_requires_its_password():
    with pytest.raises(ConfigError, match="POSTGRES_MIGRATOR_PASSWORD is not set"):
        load_migrator_config({"APP_ENV": "local", "POSTGRES_HOST": "localhost"})
