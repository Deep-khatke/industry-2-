"""FCS-PFL Versioned Data Contracts: RoundManifest, CandidateManifest, and PrivacyReceipt."""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AggregationProtocol(StrEnum):
    """Federated aggregation protocol type."""

    PLAINTEXT_FEDAVG = "PLAINTEXT_FEDAVG"
    FEDAVG = "PLAINTEXT_FEDAVG"
    SECAGG_PLUS = "SECAGG_PLUS"


class RoundStatus(StrEnum):
    """Lifecycle state machine for a federated training round."""

    CREATED = "CREATED"
    ADMITTING = "ADMITTING"
    LOCAL_TRAINING = "LOCAL_TRAINING"
    MASKED_COLLECTION = "MASKED_COLLECTION"
    UNMASKING = "UNMASKING"
    AGGREGATE_VALIDATION = "AGGREGATE_VALIDATION"
    EVALUATING = "EVALUATING"
    CANDIDATE_READY = "CANDIDATE_READY"
    ABORTED = "ABORTED"
    FAILED = "FAILED"


class CandidateStatus(StrEnum):
    """Promotion status of an aggregated model candidate."""

    TRAINED = "TRAINED"
    REGISTERED = "REGISTERED"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"


class RoundManifest(BaseModel):
    """
    RoundManifest v1: Deterministic specification and governance contract
    for a federated training round issued by the coordinator to participants.
    """

    round_id: str = Field(default_factory=lambda: f"round_{uuid.uuid4().hex[:10]}")
    job_id: str = Field(default="job_pfl_001")
    sequence: int = Field(default=1, ge=1)
    cohort: list[str] = Field(default_factory=lambda: [f"isp_{i:02d}" for i in range(1, 8)])
    base_model_digest: str = Field(..., description="SHA-256 digest of initial/global model state")
    application_digest: str = Field(default="fcs_pfl_v1.2", description="SHA-256 digest of client training code")
    feature_schema_digest: str = Field(
        default="92f73ab100db06d82b252e0c86fac983083232fb247baf1cdf57afd6ba8dcbf0",
        description="Locked 14-feature deployable_v1 schema digest",
    )
    privacy_policy_version: str = Field(default="1.2.0")
    aggregation_protocol: AggregationProtocol = Field(default=AggregationProtocol.SECAGG_PLUS)
    reconstruction_threshold: int = Field(default=5, ge=3, description="Minimum surviving shares required (SecAgg+)")
    min_completed_clients: int = Field(default=5, ge=3, description="Minimum clients required to finalize round")
    max_duration_sec: float = Field(default=1800.0, description="Max permitted round execution window")
    hyperparameters: dict[str, Any] = Field(
        default_factory=lambda: {
            "local_epochs": 2,
            "batch_size": 32,
            "learning_rate": 0.001,
            "weight_decay": 0.0001,
            "max_grad_norm": 1.0,
            "noise_multiplier": 1.1,
            "target_delta": 1e-5,
        }
    )
    nonce: str = Field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    valid_until: str = Field(default="")
    coordinator_signature: str = Field(default="fcs_dev_coordinator_signed")

    def compute_manifest_digest(self) -> str:
        """Deterministic digest of critical round parameters."""
        canonical = {
            "round_id": self.round_id,
            "job_id": self.job_id,
            "sequence": self.sequence,
            "cohort": sorted(self.cohort),
            "base_model_digest": self.base_model_digest,
            "application_digest": self.application_digest,
            "feature_schema_digest": self.feature_schema_digest,
            "aggregation_protocol": str(self.aggregation_protocol),
            "reconstruction_threshold": self.reconstruction_threshold,
            "hyperparameters": dict(sorted(self.hyperparameters.items())),
            "nonce": self.nonce,
        }
        return hashlib.sha256(json.dumps(canonical, sort_keys=True).encode("utf-8")).hexdigest()


class PrivacyReceipt(BaseModel):
    """
    Immutable receipt of private gradient expenditure tracked by each ISP's
    client-side privacy accountant before export.
    """

    receipt_id: str = Field(default_factory=lambda: f"rcpt_{uuid.uuid4().hex[:10]}")
    tenant_id: str
    round_id: str
    epsilon_spent: float
    delta_spent: float
    cumulative_epsilon: float
    cumulative_delta: float
    noise_multiplier: float
    max_grad_norm: float
    sample_rate: float
    steps_executed: int
    status: str = Field(default="RESERVED", description="RESERVED, COMMITTED, or ABORTED")
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class CandidateManifest(BaseModel):
    """
    CandidateManifest: Comprehensive provenance record for an aggregated
    federated model ready for evaluation and HMD registry promotion.
    """

    candidate_id: str = Field(default_factory=lambda: f"fed_cand_{uuid.uuid4().hex[:10]}")
    round_id: str
    model_family: str = Field(default="PyTorchMLP")
    model_digest: str
    artifact_path: str
    feature_schema_digest: str
    participating_clients: list[str]
    aggregation_protocol: AggregationProtocol
    status: CandidateStatus = Field(default=CandidateStatus.TRAINED)
    privacy_metrics: dict[str, Any] = Field(default_factory=dict)
    test_metrics: dict[str, float] = Field(default_factory=dict)
    worst_client_metrics: dict[str, float] = Field(default_factory=dict)
    authorized_by: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    activated_at: str | None = None
