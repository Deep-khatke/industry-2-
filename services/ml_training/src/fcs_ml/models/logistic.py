"""Interpretable, lightweight Logistic Regression model with training-only scaling."""

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from .base import BaseFCSModel


class LogisticRegressionModel(BaseFCSModel):
    """Reproducible Logistic Regression classifier with strictly isolated scaling."""

    def __init__(
        self,
        C: float = 1.0,
        max_iter: int = 1000,
        penalty: str = "l2",
        class_weight: str | None = "balanced",
        random_seed: int = 42,
    ) -> None:
        super().__init__("LogisticRegression", random_seed)
        self.C = C
        self.max_iter = max_iter
        self.penalty = penalty
        self.class_weight = class_weight
        self._scaler = StandardScaler()
        self._clf = LogisticRegression(
            C=self.C,
            max_iter=self.max_iter,
            class_weight=self.class_weight,
            random_state=self.random_seed,
            solver="lbfgs",
        )
        self.coef_: np.ndarray | None = None
        self.intercept_: np.ndarray | None = None
        self.n_iter_: int = 0

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        feature_names: list[str] | None = None,
    ) -> "LogisticRegressionModel":
        self.feature_names = feature_names or []
        # Fit scaler strictly on training split
        X_train_scaled = self._scaler.fit_transform(X_train)
        self._clf.fit(X_train_scaled, y_train)

        self.coef_ = self._clf.coef_
        self.intercept_ = self._clf.intercept_
        self.n_iter_ = int(self._clf.n_iter_[0]) if hasattr(self._clf, "n_iter_") else 0
        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted or self.coef_ is None or self.intercept_ is None:
            raise RuntimeError("Model is not fitted yet.")
        X_scaled = self._scaler.transform(X)
        z = np.dot(X_scaled, self.coef_.T) + self.intercept_
        z = np.clip(z, -250.0, 250.0)
        prob_1 = 1.0 / (1.0 + np.exp(-z))
        prob_0 = 1.0 - prob_1
        return np.hstack([prob_0, prob_1])

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        proba = self.predict_proba(X)
        return (proba[:, 1] >= threshold).astype(np.int64)

    def get_params(self) -> dict[str, Any]:
        return {
            "model_family": "LogisticRegression",
            "C": self.C,
            "max_iter": self.max_iter,
            "penalty": self.penalty,
            "class_weight": self.class_weight,
            "random_seed": self.random_seed,
            "n_iter": self.n_iter_,
        }

    def save(self, filepath: Path | str) -> str:
        p = Path(filepath)
        if p.suffix != ".json":
            p = p.with_suffix(".json")
        p.parent.mkdir(parents=True, exist_ok=True)
        artifact = {
            "model_family": "LogisticRegression",
            "C": self.C,
            "max_iter": self.max_iter,
            "penalty": self.penalty,
            "class_weight": self.class_weight,
            "random_seed": self.random_seed,
            "feature_names": self.feature_names,
            "coef": self.coef_.tolist() if self.coef_ is not None else [],
            "intercept": self.intercept_.tolist() if self.intercept_ is not None else [],
            "scaler_mean": self._scaler.mean_.tolist() if hasattr(self._scaler, "mean_") and self._scaler.mean_ is not None else [],
            "scaler_scale": self._scaler.scale_.tolist() if hasattr(self._scaler, "scale_") and self._scaler.scale_ is not None else [],
            "is_fitted": self.is_fitted,
        }
        content = json.dumps(artifact, indent=2)
        p.write_text(content, encoding="utf-8")
        return hashlib.sha256(p.read_bytes()).hexdigest()

    @classmethod
    def load(cls, filepath: Path | str) -> "LogisticRegressionModel":
        p = Path(filepath)
        if not p.exists() and p.with_suffix(".json").exists():
            p = p.with_suffix(".json")
        elif p.is_dir() and (p / "model.json").exists():
            p = p / "model.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        model = cls(
            C=data["C"],
            max_iter=data["max_iter"],
            penalty=data["penalty"],
            class_weight=data["class_weight"],
            random_seed=data["random_seed"],
        )
        model.feature_names = data.get("feature_names", [])
        model.coef_ = np.array(data["coef"], dtype=np.float64)
        model.intercept_ = np.array(data["intercept"], dtype=np.float64)
        model.is_fitted = data.get("is_fitted", True)

        # Restore scaler
        model._scaler.mean_ = np.array(data["scaler_mean"], dtype=np.float64)
        model._scaler.scale_ = np.array(data["scaler_scale"], dtype=np.float64)
        model._scaler.var_ = model._scaler.scale_ ** 2
        model._scaler.n_features_in_ = len(model.feature_names)

        # Re-attach to sklearn internal clf
        model._clf.coef_ = model.coef_
        model._clf.intercept_ = model.intercept_
        model._clf.classes_ = np.array([0, 1])
        return model
