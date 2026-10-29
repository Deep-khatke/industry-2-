"""Configuration and settings for FCS Platform (Phases 4-11 Hardened)."""

from enum import Enum
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
import yaml


class EnvironmentProfile(str, Enum):
    DEVELOPMENT = "DEVELOPMENT"
    INTEGRATION = "INTEGRATION"
    STAGING_REFERENCE = "STAGING_REFERENCE"
    PRODUCTION_REFERENCE = "PRODUCTION_REFERENCE"


DEFAULT_DEV_JWT_SECRET = "fcs-phase4-ephemeral-dev-secret-key-zero-cost"


class Settings(BaseModel):
    """Application settings for FCS."""

    project_name: str = "Federated Cyber Shield"
    version: str = "1.2.0"
    environment: str = os.getenv("FCS_ENV", "development").upper()
    db_path: str = os.getenv("FCS_DB_PATH", "data/fcs_phase4.db")
    backup_dir: str = os.getenv("FCS_BACKUP_DIR", "data/backups")
    model_registry_dir: str = os.getenv("FCS_MODEL_REGISTRY", "artifacts/candidate-models")
    default_model_id: str = "lightgbm_deployable_subset"

    # JWT Authentication
    jwt_secret_key: str = os.getenv("FCS_JWT_SECRET", DEFAULT_DEV_JWT_SECRET)
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = int(os.getenv("FCS_JWT_EXPIRATION_MINUTES", "1440"))

    # Security controls
    debug_mode: bool = os.getenv("FCS_DEBUG", "false").lower() in ("true", "1", "yes")
    allow_demo_credentials: bool = True
    allow_demo_endpoints: bool = True
    allow_synthetic_replay: bool = True
    enforce_mfa: bool = False
    trusted_hosts: list[str] = Field(
        default_factory=lambda: ["127.0.0.1", "localhost", "10.138.109.43"]
    )
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:8000",
            "http://localhost:8000",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://localhost:3000",
        ]
    )

    # Windowing & Ingestion
    window_duration_seconds: float = 30.0
    allowed_lateness_seconds: float = 60.0

    # Incident Management
    incident_grouping_window_seconds: int = 300  # 5 minutes grouping

    # Manual Response Policy Invariants
    max_action_duration_seconds: int = 3600  # 1 hour maximum duration
    min_action_duration_seconds: int = 60    # 1 minute minimum
    protected_ip_ranges: list[str] = Field(
        default_factory=lambda: [
            "127.0.0.1",
            "::1",
            "10.0.0.1",
            "192.168.1.1",
            "0.0.0.0/0",
            "255.255.255.255",
            "1.1.1.1",
            "8.8.8.8",
            "9.9.9.9",
        ]
    )

    # Effective response policy mode
    response_mode: str = "MANUAL"
    auto_response_enabled: bool = False  # Strictly False under ₹0 budget / Gate G13

    # Cost policy guardrail
    enforce_zero_cost: bool = True

    def model_post_init(self, __context: Any) -> None:
        """Apply environment-specific security constraints."""
        env_upper = self.environment.upper()

        # Check if caller tried to enable auto_response in production/staging
        if env_upper in ("PRODUCTION_REFERENCE", "STAGING_REFERENCE"):
            if self.auto_response_enabled:
                raise ValueError(
                    "Production Configuration Violation: AUTO_LIVE mode is strictly prohibited "
                    "under Gate G13 without physical router hardware qualification."
                )

        # Attempt to load overrides from environment yaml if present
        configs_dir = Path(__file__).resolve().parents[4] / "configs" / "environments"
        yaml_path = configs_dir / f"{env_upper.lower().replace('_', '-')}.yaml"
        if not yaml_path.exists():
            yaml_path = configs_dir / f"{env_upper.lower()}.yaml"

        if yaml_path.exists():
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                sec = cfg.get("security", {})
                if "allow_demo_credentials" in sec:
                    self.allow_demo_credentials = bool(sec["allow_demo_credentials"])
                if "allow_demo_endpoints" in sec:
                    self.allow_demo_endpoints = bool(sec["allow_demo_endpoints"])
                if "allow_synthetic_replay" in sec:
                    self.allow_synthetic_replay = bool(sec["allow_synthetic_replay"])
                if "jwt_expiration_minutes" in sec:
                    self.jwt_expiration_minutes = int(sec["jwt_expiration_minutes"])
                if "trusted_hosts" in sec:
                    self.trusted_hosts = list(sec["trusted_hosts"])
                if "cors_allowed_origins" in sec:
                    self.cors_allowed_origins = list(sec["cors_allowed_origins"])
            except Exception:
                pass

        # In non-development, enforce secure restrictions
        if env_upper != "DEVELOPMENT":
            self.debug_mode = False
            self.allow_demo_credentials = False
            self.allow_demo_endpoints = False
            self.allow_synthetic_replay = False
            self.auto_response_enabled = False

        # Validate production reference safety
        if env_upper in ("PRODUCTION_REFERENCE", "STAGING_REFERENCE"):
            self.validate_production_configuration()

    @property
    def is_development(self) -> bool:
        return self.environment.upper() == "DEVELOPMENT"

    def validate_production_configuration(self) -> None:
        """Enforces mandatory security settings for staging and production profiles."""
        if self.jwt_secret_key == DEFAULT_DEV_JWT_SECRET:
            raise ValueError(
                "Mandatory Security Setting Missing: Default ephemeral development JWT secret "
                "is prohibited in PRODUCTION_REFERENCE / STAGING_REFERENCE mode. Set FCS_JWT_SECRET."
            )
        if self.auto_response_enabled:
            raise ValueError(
                "Production Configuration Violation: AUTO_LIVE mode is strictly prohibited "
                "under Gate G13 without physical router hardware qualification."
            )
        if self.allow_demo_credentials:
            raise ValueError(
                "Mandatory Security Setting Missing: allow_demo_credentials must be False outside development."
            )
        if self.allow_demo_endpoints:
            raise ValueError(
                "Mandatory Security Setting Missing: allow_demo_endpoints must be False outside development."
            )


settings = Settings()
