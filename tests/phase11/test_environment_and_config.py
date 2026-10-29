"""Phase 11: Environment Profiles and Secure Configuration Tests."""

import pytest
from fcs_api.config import DEFAULT_DEV_JWT_SECRET, Settings


def test_environment_profile_development_defaults():
    """Verify DEVELOPMENT environment permits demo workflows and seeds."""
    cfg = Settings(environment="DEVELOPMENT")
    assert cfg.is_development is True
    assert cfg.allow_demo_credentials is True
    assert cfg.allow_demo_endpoints is True
    assert cfg.allow_synthetic_replay is True
    assert cfg.auto_response_enabled is False
    assert cfg.enforce_zero_cost is True


def test_environment_profile_integration_restrictions():
    """Verify INTEGRATION environment strictly disables demo seeds and endpoints."""
    cfg = Settings(environment="INTEGRATION", jwt_secret_key="custom-ci-secret")
    assert cfg.is_development is False
    assert cfg.allow_demo_credentials is False
    assert cfg.allow_demo_endpoints is False
    assert cfg.allow_synthetic_replay is False
    assert cfg.auto_response_enabled is False


def test_production_reference_fails_with_default_secret():
    """Verify fail-fast validation when production configuration has default secret."""
    with pytest.raises(ValueError, match="Mandatory Security Setting Missing: Default ephemeral"):
        Settings(
            environment="PRODUCTION_REFERENCE",
            jwt_secret_key=DEFAULT_DEV_JWT_SECRET,
        )


def test_production_reference_fails_if_auto_live_enabled():
    """Verify fail-fast validation if AUTO_LIVE is attempted in production profile."""
    with pytest.raises(ValueError, match="AUTO_LIVE mode is strictly prohibited"):
        Settings(
            environment="PRODUCTION_REFERENCE",
            jwt_secret_key="strong-vault-kms-managed-secret-256bit",
            **{"auto_response_enabled": True},
        )


def test_production_reference_valid_configuration():
    """Verify valid production-reference settings without executing live cloud infra."""
    cfg = Settings(
        environment="PRODUCTION_REFERENCE",
        jwt_secret_key="strong-vault-kms-managed-secret-256bit",
        auto_response_enabled=False,
    )
    assert cfg.environment == "PRODUCTION_REFERENCE"
    assert cfg.is_development is False
    assert cfg.allow_demo_credentials is False
    assert cfg.allow_demo_endpoints is False
    assert cfg.enforce_zero_cost is True
