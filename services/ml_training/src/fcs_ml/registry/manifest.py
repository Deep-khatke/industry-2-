"""ModelManifest v1 contract for versioned candidate ML models."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
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
        # Cross-component compatibility adapter for federated learning candidates
        if "model_family" not in data and "model_type" in data:
            data["model_family"] = "PyTorchMLP" if "pytorch" in data.get("model_type", "").lower() else data["model_type"]
        if "artifact_hash" not in data and "hash" in data:
            data["artifact_hash"] = data["hash"]
        if "feature_track" not in data:
            data["feature_track"] = data.get("feature_set", "deployable")
        if "feature_schema_digest" not in data:
            data["feature_schema_digest"] = "locked_v1"
        if "feature_names" not in data:
            data["feature_names"] = []
        if "dataset_manifest_digest" not in data:
            data["dataset_manifest_digest"] = "federated_partition_phase6"
        if "training_sample_count" not in data:
            data["training_sample_count"] = 0
        if "validation_sample_count" not in data:
            data["validation_sample_count"] = 0
        if "test_sample_count" not in data:
            data["test_sample_count"] = 0
        if "artifact_path" not in data:
            data["artifact_path"] = str(Path(filepath).parent / "model.pt")
        return cls(**data)
