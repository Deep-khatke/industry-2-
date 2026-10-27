"""PartitionManifest contracts for 7-client simulated ISP federated learning."""

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class PartitionRegime(StrEnum):
    """Federated partitioning distribution regimes."""

    IID = "IID"
    MODERATE_NON_IID = "MODERATE_NON_IID"
    STRONG_NON_IID = "STRONG_NON_IID"


class ClientPartitionInfo(BaseModel):
    """Metadata and statistics for a single simulated ISP partition."""

    client_id: str = Field(..., description="Logical client identifier (e.g. isp_01)")
    tenant_id_mapping: str = Field(..., description="Mapped Phase 1 tenant identifier (e.g. tenant-isp-alpha)")
    assigned_record_count: int = Field(..., ge=0, description="Total number of training records allocated")
    assigned_record_digest: str = Field(..., description="SHA-256 digest of sorted row keys for this client")
    class_distribution: dict[str, int] = Field(default_factory=dict, description="Class label frequencies")
    source_distribution: dict[str, int] = Field(default_factory=dict, description="Dataset source frequencies")
    output_filename: str = Field(..., description="Partition artifact filename relative to processed/partitions")
    output_checksum: str = Field(..., description="SHA-256 hash of output parquet file")


class FederatedPartitionSetManifest(BaseModel):
    """
    Contract recording the complete multi-client partition set across the 7 simulated ISPs
    for a specific distribution regime (IID, moderate non-IID, or strong non-IID).
    """

    manifest_schema_version: str = Field(default="1.0.0", description="Contract version")
    regime: PartitionRegime = Field(..., description="Partition regime (IID, MODERATE_NON_IID, STRONG_NON_IID)")
    parent_dataset_digest: str = Field(..., description="SHA-256 digest of clean pre-partitioned dataset")
    seed: int = Field(default=42, description="Random seed used for deterministic allocation")
    dirichlet_alpha: float | None = Field(
        default=None,
        description="Dirichlet concentration parameter alpha used for non-IID class skew",
    )
    total_training_records: int = Field(..., ge=0, description="Total training records partitioned across all clients")
    client_partitions: dict[str, ClientPartitionInfo] = Field(
        ...,
        description="Mapping from client_id (isp_01 .. isp_07) to client partition metadata",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Partition generation timestamp in UTC",
    )

    def to_canonical_json(self) -> str:
        """Deterministic JSON string representation with sorted keys."""
        return json.dumps(self.model_dump(mode="json"), sort_keys=True)

    def compute_manifest_digest(self) -> str:
        """SHA-256 digest of canonical partition set manifest."""
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()
