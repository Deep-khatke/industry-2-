"""Isolation Forest unsupervised anomaly detector for ISP-specific traffic profiling."""

import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from .base import BaseFCSModel


class IsolationForestAnomalyModel(BaseFCSModel):
    """
    ISP-specific anomaly detector.
    Trained strictly on benign tenant traffic baselines without attack contamination.
    Produces calibrated anomaly probability scores bounded in [0.0, 1.0].
    """

    def __init__(
        self,
        n_estimators: int = 100,
        contamination: float = 0.05,
        max_samples: str | int | float = "auto",
        random_seed: int = 42,
        tenant_id: str = "global",
    ) -> None:
        super().__init__("IsolationForest", random_seed)
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.max_samples = max_samples
        self.tenant_id = tenant_id
        self._scaler = StandardScaler()
        self._clf = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            max_samples=self.max_samples,
            random_state=self.random_seed,
            n_jobs=2,
        )
        self.decision_threshold_: float = 0.0
        self.sigmoid_scale_: float = 8.0

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray | None = None,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        feature_names: list[str] | None = None,
    ) -> "IsolationForestAnomalyModel":
        """
        Fit model on benign traffic.
        If y_train is passed, only samples where y_train == 0 (benign) are used to fit baseline.
        """
        self.feature_names = feature_names or []
        if y_train is not None:
            benign_mask = y_train == 0
            if np.sum(benign_mask) > 0:
                X_fit = X_train[benign_mask]
            else:
                X_fit = X_train
        else:
            X_fit = X_train

        # Clean NaNs/Infs
        X_clean = np.nan_to_num(X_fit, nan=0.0, posinf=1e6, neginf=-1e6)

        # Fit training-only scaler
        X_scaled = self._scaler.fit_transform(X_clean)
        self._clf.fit(X_scaled)

        # Calibrate decision threshold on training baseline (contamination percentile)
        scores = self._clf.decision_function(X_scaled)
        self.decision_threshold_ = float(np.percentile(scores, self.contamination * 100.0))
        self.is_fitted = True
        return self

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        """Return raw Isolation Forest decision score (negative = anomaly, positive = normal)."""
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted.")
        X_clean = np.nan_to_num(X, nan=0.0, posinf=1e6, neginf=-1e6)
        X_scaled = self._scaler.transform(X_clean)
        return self._clf.decision_function(X_scaled)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict probability scores.
        Maps decision score to anomaly probability using calibrated sigmoid:
        s < threshold implies high anomaly probability.
        Returns shape (N, 2): [P(Normal), P(Anomaly)].
        """
        scores = self.decision_function(X)
        # Shift relative to decision threshold and apply inverted sigmoid
        # When score is far below threshold -> high anomaly probability
        z = -self.sigmoid_scale_ * (scores - self.decision_threshold_)
        p_anomaly = 1.0 / (1.0 + np.exp(np.clip(-z, -50.0, 50.0)))
        p_anomaly = np.clip(p_anomaly, 0.0, 1.0)
        p_normal = 1.0 - p_anomaly
        return np.vstack([p_normal, p_anomaly]).T

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Predict binary discrete label: 1 = Anomaly, 0 = Normal."""
        proba = self.predict_proba(X)
        return (proba[:, 1] >= threshold).astype(np.int64)

    def get_params(self) -> dict[str, Any]:
        return {
            "model_family": "IsolationForest",
            "n_estimators": self.n_estimators,
            "contamination": self.contamination,
            "max_samples": self.max_samples,
            "random_seed": self.random_seed,
            "tenant_id": self.tenant_id,
            "decision_threshold": self.decision_threshold_,
            "sigmoid_scale": self.sigmoid_scale_,
            "feature_names": self.feature_names,
            "is_fitted": self.is_fitted,
        }

    def save(self, filepath: Path | str) -> str:
        """Save joblib serialized classifier and sidecar metadata JSON with SHA-256."""
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)

        joblib_path = p.with_suffix(".joblib")
        meta_path = p.with_suffix(".json")

        joblib.dump(self._clf, joblib_path, compress=3)

        meta = {
            "model_family": "IsolationForest",
            "n_estimators": self.n_estimators,
            "contamination": self.contamination,
            "max_samples": self.max_samples,
            "random_seed": self.random_seed,
            "tenant_id": self.tenant_id,
            "decision_threshold": self.decision_threshold_,
            "sigmoid_scale": self.sigmoid_scale_,
            "feature_names": self.feature_names,
            "scaler_mean": self._scaler.mean_.tolist() if hasattr(self._scaler, "mean_") and self._scaler.mean_ is not None else [],
            "scaler_scale": self._scaler.scale_.tolist() if hasattr(self._scaler, "scale_") and self._scaler.scale_ is not None else [],
            "is_fitted": self.is_fitted,
        }
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        combined = joblib_path.read_bytes() + meta_path.read_bytes()
        return hashlib.sha256(combined).hexdigest()

    @classmethod
    def load(cls, filepath: Path | str) -> "IsolationForestAnomalyModel":
        p = Path(filepath)
        joblib_path = p.with_suffix(".joblib")
        meta_path = p.with_suffix(".json")

        if not joblib_path.exists() and p.exists() and p.suffix == ".joblib":
            joblib_path = p
            meta_path = p.with_suffix(".json")

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        model = cls(
            n_estimators=meta["n_estimators"],
            contamination=meta["contamination"],
            max_samples=meta["max_samples"],
            random_seed=meta["random_seed"],
            tenant_id=meta.get("tenant_id", "global"),
        )
        model.feature_names = meta.get("feature_names", [])
        model.decision_threshold_ = meta.get("decision_threshold", 0.0)
        model.sigmoid_scale_ = meta.get("sigmoid_scale", 8.0)
        model.is_fitted = meta.get("is_fitted", True)

        model._clf = joblib.load(joblib_path)

        if meta.get("scaler_mean"):
            model._scaler.mean_ = np.array(meta["scaler_mean"], dtype=np.float64)
            model._scaler.scale_ = np.array(meta["scaler_scale"], dtype=np.float64)
            model._scaler.var_ = model._scaler.scale_ ** 2
            model._scaler.n_features_in_ = len(model.feature_names)

        return model
