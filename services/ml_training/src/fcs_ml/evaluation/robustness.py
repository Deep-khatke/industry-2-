"""Distribution shift and robustness evaluation against noise and missing features."""

from typing import Any

import numpy as np

from fcs_ml.models.base import BaseFCSModel

from .metrics import compute_binary_metrics


class RobustnessEvaluator:
    """Evaluates model performance degradation under simulated network telemetry impairments."""

    @staticmethod
    def evaluate_missing_features(
        model: BaseFCSModel,
        X: np.ndarray,
        y: np.ndarray,
        missing_rates: list[float] | None = None,
        random_seed: int = 42,
    ) -> list[dict[str, Any]]:
        """Simulate random telemetry loss where features are unobserved/nullified."""
        missing_rates = missing_rates or [0.05, 0.10, 0.20]
        rng = np.random.default_rng(random_seed)
        results = []

        # Baseline with zero missingness
        base_proba = model.predict_proba(X)
        base_metrics = compute_binary_metrics(y, base_proba)
        results.append({
            "impairment": "missing_features",
            "rate": 0.0,
            "f1": base_metrics["f1"],
            "pr_auc": base_metrics["pr_auc"],
            "fpr": base_metrics["fpr"],
        })

        for rate in missing_rates:
            X_corrupt = X.copy()
            mask = rng.random(size=X.shape) < rate
            X_corrupt[mask] = 0.0  # Nullified/defaulted features

            proba = model.predict_proba(X_corrupt)
            m = compute_binary_metrics(y, proba)
            results.append({
                "impairment": "missing_features",
                "rate": float(rate),
                "f1": m["f1"],
                "pr_auc": m["pr_auc"],
                "fpr": m["fpr"],
                "f1_delta": float(m["f1"] - base_metrics["f1"]),
            })

        return results

    @staticmethod
    def evaluate_gaussian_noise(
        model: BaseFCSModel,
        X: np.ndarray,
        y: np.ndarray,
        noise_levels: list[float] | None = None,
        random_seed: int = 42,
    ) -> list[dict[str, Any]]:
        """Simulate network jitter and statistical noise in volumetric flow features."""
        noise_levels = noise_levels or [0.05, 0.10, 0.25]
        rng = np.random.default_rng(random_seed)
        results = []

        base_proba = model.predict_proba(X)
        base_metrics = compute_binary_metrics(y, base_proba)
        results.append({
            "impairment": "gaussian_noise",
            "noise_std": 0.0,
            "f1": base_metrics["f1"],
            "pr_auc": base_metrics["pr_auc"],
            "fpr": base_metrics["fpr"],
        })

        # Calculate standard deviation per feature
        feature_stds = np.std(X, axis=0)
        feature_stds[feature_stds == 0] = 1.0

        for noise_scale in noise_levels:
            noise = rng.normal(loc=0.0, scale=noise_scale, size=X.shape) * feature_stds
            X_noisy = X + noise

            proba = model.predict_proba(X_noisy)
            m = compute_binary_metrics(y, proba)
            results.append({
                "impairment": "gaussian_noise",
                "noise_std": float(noise_scale),
                "f1": m["f1"],
                "pr_auc": m["pr_auc"],
                "fpr": m["fpr"],
                "f1_delta": float(m["f1"] - base_metrics["f1"]),
            })

        return results
