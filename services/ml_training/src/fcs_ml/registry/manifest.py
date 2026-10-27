"""ModelManifest v1 contract for versioned candidate ML models."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class ModelManifest(BaseModel):
    """Immutable metadata contract for candidate intrusion detection models."""

    manifest_schema_version: str = "1.0.0"
    model_id: str
    model_family: str
    version: str = "1.0.0"
    feature_track: str
    feature_schema_digest: str
    feature_names: list[str]
    preprocessing_digest: str = "default_phase2"
    dataset_manifest_digest: str
    training_sample_count: int
    validation_sample_count: int
    test_sample_count: int
    validation_threshold: float = 0.5
    calibration_method: str = "none"
    test_metrics: dict[str, Any] = Field(default_factory=dict)
    artifact_hash: str
    artifact_path: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    git_commit: str = "phase3-dev"

    def to_canonical_json(self) -> str:
        """Deterministic canonical JSON serialization for digest computation."""
        d = self.model_dump()
        return json.dumps(d, sort_keys=True, indent=2)

    def compute_manifest_digest(self) -> str:
        """Compute SHA-256 digest of the canonical manifest representation."""
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_file(cls, filepath: str) -> "ModelManifest":
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
