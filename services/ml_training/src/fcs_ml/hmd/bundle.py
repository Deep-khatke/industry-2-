"""DetectionBundle specification, validation, authorized activation, and rollback."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from fcs_ml.registry.registry import CandidateModelRegistry


class DetectionBundle(BaseModel):
    """
    Immutable specification of an authorized multi-model detection ensemble.
    Binds constituent model artifacts by SHA-256 digest to prevent unauthorized tampering.
    """

    bundle_id: str = Field(..., description="Unique bundle identifier, e.g. fcs-hmd-bundle-v1")
    version: str = Field(default="1.2.0", description="Bundle release version")
    general_model_id: str = Field(..., description="Identifier of general threat detector")
    anomaly_model_id: str = Field(..., description="Identifier of tenant anomaly detector")
    specialist_model_ids: list[str] = Field(
        default_factory=list,
        description="List of specialist model identifiers (DDoS, Scanning, etc.)",
    )
    model_hashes: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of model_id to verified SHA-256 artifact hash",
    )
    bundle_digest: str = Field(
        default="",
        description="Deterministic SHA-256 digest of the entire bundle definition",
    )
    authorized_by: str = Field(default="system_bootstrap", description="Authorized admin identity")
    status: str = Field(default="ACTIVE", description="ACTIVE, STAGING, or ROLLED_BACK")
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    activated_at: str | None = None

    def compute_bundle_digest(self) -> str:
        """Compute deterministic SHA-256 digest of ordered constituent models and hashes."""
        canonical = {
            "bundle_id": self.bundle_id,
            "version": self.version,
            "general_model_id": self.general_model_id,
            "anomaly_model_id": self.anomaly_model_id,
            "specialist_model_ids": sorted(self.specialist_model_ids),
            "model_hashes": dict(sorted(self.model_hashes.items())),
        }
        serialized = json.dumps(canonical, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def seal(self) -> "DetectionBundle":
        """Compute and lock bundle_digest."""
        self.bundle_digest = self.compute_bundle_digest()
        return self

    @classmethod
    def load(cls, path: Path | str) -> "DetectionBundle":
        """Load detection bundle from JSON file."""
        p = Path(path)
        return cls.model_validate_json(p.read_text(encoding="utf-8"))


class BundleValidator:
    """Validates constituent model artifacts, hashes, and schema compatibility."""

    @staticmethod
    def validate(bundle: DetectionBundle, registry: CandidateModelRegistry) -> dict[str, Any]:
        """
        Verify that all constituent models exist in registry and match recorded hashes.
        """
        errors: list[str] = []
        verified_models: list[str] = []

        all_models = [bundle.general_model_id, bundle.anomaly_model_id] + bundle.specialist_model_ids

        for m_id in all_models:
            try:
                res = registry.verify_model_artifact(m_id)
                actual_h = res.get("actual_hash")
                if not res.get("integrity_verified", False):
                    errors.append(f"Model '{m_id}' SHA-256 hash mismatch: expected {res.get('recorded_hash')}, got {actual_h}")
                elif m_id in bundle.model_hashes and bundle.model_hashes[m_id] != actual_h:
                    errors.append(f"Model '{m_id}' SHA-256 mismatch against bundle definition: bundle recorded {bundle.model_hashes[m_id]}, actual artifact has {actual_h}")
                else:
                    verified_models.append(m_id)
            except Exception as e:
                errors.append(f"Model '{m_id}' verification failed: {e}")

        # Check bundle digest integrity
        expected_digest = bundle.compute_bundle_digest()
        if bundle.bundle_digest and bundle.bundle_digest != expected_digest:
            errors.append(f"Bundle digest tampering detected: expected {expected_digest}, recorded {bundle.bundle_digest}")

        is_valid = len(errors) == 0
        return {
            "bundle_id": bundle.bundle_id,
            "is_valid": is_valid,
            "verified_models": verified_models,
            "errors": errors,
            "bundle_digest": expected_digest,
        }
