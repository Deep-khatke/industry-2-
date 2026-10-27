"""ML security verification and adversarial input defense."""

from pathlib import Path
from typing import Any

import numpy as np

from fcs_ml.features.selector import TargetLeakageError
from fcs_ml.registry.manifest import ModelManifest


class MLSecurityError(Exception):
    """Raised when an ML security vulnerability, tampering, or leakage is detected."""


class MLSecurityValidator:
    """Enforces zero-trust ML security checks on artifacts, inputs, and boundaries."""

    @staticmethod
    def audit_model_manifest(manifest: ModelManifest) -> dict[str, Any]:
        """Verify model manifest security properties."""
        findings = []

        # 1. Feature schema check
        if not manifest.feature_names:
            findings.append("CRITICAL: Manifest contains 0 feature names.")

        # 2. Check for target leakage in feature names
        for feat in manifest.feature_names:
            if feat.lower() in {"attack", "label", "canonical_attack_label", "binary_label", "dataset_source"}:
                raise TargetLeakageError(f"Target column '{feat}' found in manifest feature list!")

        # 3. Artifact path check
        p = Path(manifest.artifact_path)
        if not p.exists() and not p.with_suffix(".txt").exists() and not p.with_suffix(".pt").exists():
            findings.append(f"HIGH: Artifact path '{p}' does not exist on disk.")

        return {
            "model_id": manifest.model_id,
            "passed": len(findings) == 0,
            "findings": findings,
        }

    @staticmethod
    def validate_inference_inputs(X: np.ndarray, expected_dim: int) -> None:
        """Validate input feature matrix shape and numeric sanity."""
        if X.ndim != 2:
            raise MLSecurityError(f"Input feature matrix must be 2D, got shape {X.shape}")

        if X.shape[1] != expected_dim:
            raise MLSecurityError(
                f"Feature dimension mismatch: expected {expected_dim} features, got {X.shape[1]}"
            )

        if np.isnan(X).any():
            raise MLSecurityError("Malicious/corrupted input: NaN detected in feature vector without sanitizer.")

        if np.isinf(X).any():
            raise MLSecurityError("Malicious/corrupted input: Infinite values detected in feature vector.")
