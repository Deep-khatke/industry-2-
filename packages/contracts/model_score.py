"""ModelScore v1 contract for FCS-HMD Hierarchical Multi-Model Intrusion Detection."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ModelType(StrEnum):
    """Categorical taxonomy of models in the FCS-HMD hierarchy."""

    GENERAL_DETECTOR = "GENERAL_DETECTOR"
    ANOMALY_DETECTOR = "ANOMALY_DETECTOR"
    DDOS_SPECIALIST = "DDOS_SPECIALIST"
    SCANNING_SPECIALIST = "SCANNING_SPECIALIST"
    BOTNET_SPECIALIST = "BOTNET_SPECIALIST"
    RULE_ENGINE = "RULE_ENGINE"


class ScoringStatus(StrEnum):
    """Operational scoring outcome status for an individual model."""

    SCORED = "SCORED"
    ABSTAIN = "ABSTAIN"
    UNCERTAIN = "UNCERTAIN"
    TIMEOUT = "TIMEOUT"
    MISSING = "MISSING"
    ERROR = "ERROR"
    BYPASSED = "BYPASSED"


class ModelScore(BaseModel):
    """
    ModelScore v1 canonical contract.
    Represents an immutable, calibrated inference output from any component in the FCS-HMD hierarchy.
    """

    model_id: str = Field(..., description="Unique model identifier")
    model_type: ModelType = Field(..., description="Taxonomy classification of the model")
    version: str = Field(default="1.2.0", description="Model semantic version")
    raw_score: float = Field(default=0.0, description="Raw uncalibrated score or anomaly distance")
    calibrated_probability: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Calibrated threat probability in [0.0, 1.0]",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Model confidence estimate in [0.0, 1.0]",
    )
    threshold_applied: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Decision threshold used to assign discrete class",
    )
    prediction: int = Field(
        default=0,
        description="Discrete class: 0 = Benign/Normal, 1 = Attack/Anomaly",
    )
    predicted_label: str = Field(
        default="Benign",
        description="Human-readable label ('Benign', 'DDoS', 'Scanning', etc.)",
    )
    is_uncertain: bool = Field(
        default=False,
        description="True if calibrated probability falls inside the uncertainty boundary",
    )
    status: ScoringStatus = Field(
        default=ScoringStatus.SCORED,
        description="Operational scoring status",
    )
    latency_microseconds: float = Field(
        default=0.0,
        ge=0.0,
        description="CPU inference latency in microseconds",
    )
    features_used: list[str] = Field(
        default_factory=list,
        description="Ordered list of feature names consumed for scoring",
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="List of explainability reason codes or feature contribution indicators",
    )
    tenant_context: str = Field(
        default="global",
        description="Tenant identifier for tenancy-isolated models",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="UTC timestamp of score generation",
    )
    network_action_executed: bool = Field(
        default=False,
        description="Strict safety invariant: all ML models output threat evidence only (ALWAYS False)",
    )

    def is_threat(self) -> bool:
        """Helper to determine whether this score is an active positive detection."""
        return self.status == ScoringStatus.SCORED and self.prediction == 1

    @classmethod
    def missing(
        cls,
        model_id: str,
        model_type: ModelType,
        tenant_context: str = "global",
        reason: str = "Model artifact not found",
    ) -> "ModelScore":
        """Factory for missing model behavior without fabricating benign scores."""
        return cls(
            model_id=model_id,
            model_type=model_type,
            raw_score=-1.0,
            calibrated_probability=0.0,
            confidence=0.0,
            threshold_applied=0.5,
            prediction=-1,
            predicted_label="UNKNOWN",
            is_uncertain=True,
            status=ScoringStatus.MISSING,
            reason_codes=[f"MISSING: {reason}"],
            tenant_context=tenant_context,
            network_action_executed=False,
        )

    @classmethod
    def timeout(
        cls,
        model_id: str,
        model_type: ModelType,
        budget_us: float,
        tenant_context: str = "global",
    ) -> "ModelScore":
        """Factory for specialist timeout without failing overall pipeline."""
        return cls(
            model_id=model_id,
            model_type=model_type,
            raw_score=-1.0,
            calibrated_probability=0.0,
            confidence=0.0,
            threshold_applied=0.5,
            prediction=-1,
            predicted_label="TIMEOUT",
            is_uncertain=True,
            status=ScoringStatus.TIMEOUT,
            latency_microseconds=budget_us,
            reason_codes=[f"TIMEOUT: Exceeded CPU latency budget {budget_us:.1f}us"],
            tenant_context=tenant_context,
            network_action_executed=False,
        )

    @classmethod
    def bypassed(
        cls,
        model_id: str,
        model_type: ModelType,
        reason: str,
        tenant_context: str = "global",
    ) -> "ModelScore":
        """Factory when model is conditionally skipped by the router."""
        return cls(
            model_id=model_id,
            model_type=model_type,
            raw_score=0.0,
            calibrated_probability=0.0,
            confidence=1.0,
            threshold_applied=0.5,
            prediction=0,
            predicted_label="BYPASSED",
            is_uncertain=False,
            status=ScoringStatus.BYPASSED,
            reason_codes=[f"ROUTER_BYPASS: {reason}"],
            tenant_context=tenant_context,
            network_action_executed=False,
        )
