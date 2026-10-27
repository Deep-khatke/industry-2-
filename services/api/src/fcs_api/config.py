"""Configuration and settings for FCS Phase 4 Backend."""

import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings for FCS Phase 4."""

    project_name: str = "Federated Cyber Shield"
    version: str = "1.2.0"
    environment: str = os.getenv("FCS_ENV", "development")
    db_path: str = os.getenv("FCS_DB_PATH", "data/fcs_phase4.db")
    model_registry_dir: str = os.getenv("FCS_MODEL_REGISTRY", "artifacts/candidate-models")
    default_model_id: str = "lightgbm_deployable_subset"

    # JWT Authentication
    jwt_secret_key: str = os.getenv("FCS_JWT_SECRET", "fcs-phase4-ephemeral-dev-secret-key-zero-cost")
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440  # 24 hours

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
        ]
    )

    # Effective response policy mode
    response_mode: str = "MANUAL"
    auto_response_enabled: bool = False  # Strictly False in Phase 4


settings = Settings()
