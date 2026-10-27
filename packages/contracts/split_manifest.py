"""SplitManifest contract recording leakage-safe train/val/test assignments."""

import hashlib
import json
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class SplitManifest(BaseModel):
    """
    Contract recording the exact partitioning of data rows into train, validation,
    and test sets, along with holdout sources and leakage validation guarantees.
    """

    manifest_schema_version: str = Field(default="1.0.0", description="Contract version")
    split_id: str = Field(..., description="Unique split identifier (e.g. split-group-seed-42-v1)")
    dataset_digest: str = Field(..., description="SHA-256 digest of clean pre-split dataset artifact")
    grouping_policy: str = Field(
        default="GROUP_AWARE_PREFIX",
        description="Grouping strategy used: 'GROUP_AWARE_PREFIX', 'TIME_AWARE', 'SOURCE_HOLDOUT', 'FALLBACK_RANDOM'",
    )
    time_policy: str = Field(
        default="TEMPORAL_ORDERED",
        description="Time handling policy for flow timestamps",
    )
    seed: int = Field(default=42, description="Random seed used for deterministic assignment")
    ratios: dict[str, float] = Field(
        default_factory=lambda: {"train": 0.70, "val": 0.15, "test": 0.15},
        description="Target split proportions",
    )
    row_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Actual row counts per split (train, val, test, holdout)",
    )
    train_record_digest: str = Field(..., description="SHA-256 digest of sorted train record IDs or keys")
    val_record_digest: str = Field(..., description="SHA-256 digest of sorted validation record IDs or keys")
    test_record_digest: str = Field(..., description="SHA-256 digest of sorted test record IDs or keys")
    independent_holdout_sources: list[str] = Field(
        default_factory=list,
        description="Source dataset IDs completely excluded from training and reserved for zero-shot generalization test",
    )
    leakage_warnings: list[str] = Field(
        default_factory=list,
        description="Warnings regarding lack of grouping fields or near-duplicate observations",
    )
    class_distribution: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="Class counts for train, val, test",
    )
    source_distribution: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="Source dataset counts for train, val, test",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of split creation in UTC",
    )

    def to_canonical_json(self) -> str:
        """Deterministic JSON string representation with sorted keys."""
        return json.dumps(self.model_dump(mode="json"), sort_keys=True)

    def compute_manifest_digest(self) -> str:
        """SHA-256 hash of canonical split manifest."""
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()
