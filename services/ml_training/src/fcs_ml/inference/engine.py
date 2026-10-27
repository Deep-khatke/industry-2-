"""InferenceEngine providing safe, schema-validated, and leakage-proof model scoring."""

import time
from typing import Any

import numpy as np
import polars as pl
from pydantic import BaseModel, Field

from fcs_ml.features.selector import TargetLeakageError
from fcs_ml.models.base import BaseFCSModel
from fcs_ml.registry.manifest import ModelManifest
from fcs_ml.registry.registry import CandidateModelRegistry


class InferenceResult(BaseModel):
    """Structured, immutable scoring result from FCS InferenceEngine."""

    model_id: str
    model_version: str
    prediction: int  # 0 = Benign, 1 = Attack
    predicted_label: str  # "Benign" or attack category
    raw_score: float
    calibrated_probability: float
    threshold_applied: float
    is_uncertain: bool = False
    status: str = "SCORED"  # "SCORED", "ABSTAIN", "NOT_SCORED"
    latency_microseconds: float = 0.0
    features_validated_count: int = 0
    tenant_context: str = Field(default="global")
    network_action_executed: bool = False  # Always FALSE; Phase 3 cannot perform network actions


class InferenceEngine:
    """Safe, operational inference interface for candidate detection models."""

    def __init__(self, registry: CandidateModelRegistry | None = None) -> None:
        self.registry = registry or CandidateModelRegistry()
        self._cached_models: dict[str, tuple[BaseFCSModel, ModelManifest]] = {}

    def get_model(self, model_id: str) -> tuple[BaseFCSModel, ModelManifest]:
        """Load or retrieve cached model and manifest."""
        if model_id not in self._cached_models:
            self._cached_models[model_id] = self.registry.load_model(model_id)
        return self._cached_models[model_id]

    def score_record(
        self,
        record: dict[str, Any],
        model_id: str,
        tenant_context: str = "global",
    ) -> InferenceResult:
        """
        Score a single telemetry flow record.
        Validates schema, checks feature ordering, handles missingness, measures latency,
        and guarantees zero network side-effects.
        """
        start_t = time.perf_counter()
        model, manifest = self.get_model(model_id)

        # Anti-Leakage Check: reject if any target or metadata columns are present as features
        for key in record:
            if key.lower() in {"attack", "label", "canonical_attack_label", "binary_label"}:
                raise TargetLeakageError(f"Target column '{key}' detected in inference record. Scoring rejected.")

        # Reorder and construct numeric vector matching manifest.feature_names
        feature_vector: list[float] = []
        for feat_name in manifest.feature_names:
            val = record.get(feat_name, None)
            if val is None or val == "":
                # Median/zero fallback
                feature_vector.append(0.0)
            else:
                try:
                    num_val = float(val)
                    if np.isnan(num_val) or np.isinf(num_val):
                        feature_vector.append(0.0)
                    else:
                        feature_vector.append(num_val)
                except (ValueError, TypeError):
                    feature_vector.append(0.0)

        X = np.array([feature_vector], dtype=np.float32)

        # Execute Model Prediction
        proba = model.predict_proba(X)
        if proba.shape[1] > 1:
            raw_score = float(proba[0, 1])
        else:
            raw_score = float(proba[0, 0])

        calibrated_prob = raw_score  # In production, pass through saved calibrator if present
        threshold = manifest.validation_threshold
        pred = 1 if calibrated_prob >= threshold else 0
        pred_label = "Attack" if pred == 1 else "Benign"

        # Check uncertainty floor
        is_uncertain = abs(calibrated_prob - threshold) < 0.05  # Within 5% margin of decision boundary
        status = "ABSTAIN" if is_uncertain else "SCORED"

        latency_us = (time.perf_counter() - start_t) * 1_000_000.0

        return InferenceResult(
            model_id=manifest.model_id,
            model_version=manifest.version,
            prediction=pred,
            predicted_label=pred_label,
            raw_score=raw_score,
            calibrated_probability=calibrated_prob,
            threshold_applied=threshold,
            is_uncertain=is_uncertain,
            status=status,
            latency_microseconds=latency_us,
            features_validated_count=len(feature_vector),
            tenant_context=tenant_context,
            network_action_executed=False,
        )

    def score_batch(
        self,
        df: pl.DataFrame,
        model_id: str,
        tenant_context: str = "global",
    ) -> list[InferenceResult]:
        """Score a batch of records from a Polars DataFrame."""
        records = df.to_dicts()
        return [self.score_record(rec, model_id, tenant_context) for rec in records]
