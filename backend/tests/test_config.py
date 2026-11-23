"""Tests for application configuration and validation."""

import pytest
from pydantic import ValidationError
from app.core.config import Settings


def test_default_settings():
    """Verify default configuration values without loading local .env overrides."""
    settings = Settings(_env_file=None)
    assert settings.PROJECT_NAME == "Converge AI — Conference Agent Network"
    assert settings.VERSION == "0.1.0"
    assert settings.ENVIRONMENT == "development"
    assert settings.API_V1_PREFIX == "/converge-api/v1"
    assert settings.HOST == "127.0.0.1"
    assert settings.PORT == 8030
    assert settings.LOG_LEVEL == "INFO"
    assert settings.DATABASE_URL is None
    assert settings.MIGRATION_DATABASE_URL is None
    assert settings.TEST_DATABASE_URL is None
    assert not settings.is_production()
    assert not settings.is_test()


def test_api_prefix_normalization():
    """Verify API prefix normalization logic."""
    s1 = Settings(_env_file=None, API_V1_PREFIX="api/v1")
    assert s1.API_V1_PREFIX == "/api/v1"

    s2 = Settings(_env_file=None, API_V1_PREFIX="/api/v1/")
    assert s2.API_V1_PREFIX == "/api/v1"

    with pytest.raises(ValidationError):
        Settings(_env_file=None, API_V1_PREFIX="/")


def test_invalid_port_validation():
    """Verify validation fails on out-of-range port."""
    with pytest.raises(ValidationError):
        Settings(_env_file=None, PORT=80)  # Privileged port < 1024

    with pytest.raises(ValidationError):
        Settings(_env_file=None, PORT=70000)  # Exceeds max port 65535


def test_environment_helper_methods():
    """Verify environment detection helpers."""
    s_prod = Settings(_env_file=None, ENVIRONMENT="production")
    assert s_prod.is_production()
    assert not s_prod.is_test()

    s_test = Settings(_env_file=None, ENVIRONMENT="test")
    assert s_test.is_test()
    assert not s_prod.is_test()
