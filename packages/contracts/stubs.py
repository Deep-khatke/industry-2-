"""Future-compatible contract stubs for Phase 2/3 architecture interfaces."""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class DetectionAlertStub(BaseModel):
    """
    Contract stub for future Phase 2 Hierarchical Multi-Model Detection (FCS-HMD).
    Enables pipeline contracts to remain stable when anomaly engines are integrated.
    """

    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    event_id: str
    detection_model: str = "stub_heuristic_v1"
    anomaly_score: float = Field(default=0.0, ge=0.0, le=1.0)
    threat_category: str = "UNCLASSIFIED"
    recommended_action: str = "MANUAL_REVIEW"  # Per FCS v1.2 rule: Manual response remains default
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class FederatedWeightsStub(BaseModel):
    """
    Contract stub for future Phase 2 Flower federated learning weight exchanges.
    Enables tensor serialization format to be planned without running FL training.
    """

    round_id: int = 0
    tenant_id: str
    model_version: str = "v1.2-stub"
    weight_layers_shape: list[list[int]] = Field(default_factory=list)
    differential_privacy_epsilon: float = 1.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
