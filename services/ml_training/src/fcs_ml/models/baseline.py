"""Dummy baseline classifier for measuring non-predictive baseline performance."""

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.dummy import DummyClassifier

from .base import BaseFCSModel


class DummyBaselineClassifier(BaseFCSModel):
    """Dummy baseline establishing reference accuracy without learned intelligence."""

    def __init__(self, strategy: str = "prior", random_seed: int = 42) -> None:
        super().__init__("DummyBaseline", random_seed)
        self.strategy = strategy
        self._clf = DummyClassifier(strategy=self.strategy, random_state=self.random_seed)
        self.class_prior_: float = 0.5

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        feature_names: list[str] | None = None,
    ) -> "DummyBaselineClassifier":
        self.feature_names = feature_names or []
        self._clf.fit(X_train, y_train)
        self.class_prior_ = float(np.mean(y_train == 1)) if len(y_train) > 0 else 0.5
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet.")
        proba = self.predict_proba(X)
        if proba.shape[1] > 1:
            return (proba[:, 1] >= threshold).astype(np.int64)
        return (proba[:, 0] >= threshold).astype(np.int64)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet.")
        p1 = self.class_prior_
        p0 = 1.0 - p1
        return np.column_stack([np.full(len(X), p0), np.full(len(X), p1)])

    def get_params(self) -> dict[str, Any]:
        return {
            "model_family": "DummyBaseline",
            "strategy": self.strategy,
            "random_seed": self.random_seed,
            "class_prior": self.class_prior_,
        }

    def save(self, filepath: Path | str) -> str:
        p = Path(filepath)
        if p.suffix != ".json":
            p = p.with_suffix(".json")
        p.parent.mkdir(parents=True, exist_ok=True)
        meta = {
            "model_family": "DummyBaseline",
            "strategy": self.strategy,
            "random_seed": self.random_seed,
            "class_prior": self.class_prior_,
            "feature_names": self.feature_names,
            "is_fitted": self.is_fitted,
        }
        content = json.dumps(meta, indent=2)
        p.write_text(content, encoding="utf-8")
        return hashlib.sha256(p.read_bytes()).hexdigest()

    @classmethod
    def load(cls, filepath: Path | str) -> "DummyBaselineClassifier":
        p = Path(filepath)
        if not p.exists() and p.with_suffix(".json").exists():
            p = p.with_suffix(".json")
        data = json.loads(p.read_text(encoding="utf-8"))
        model = cls(strategy=data["strategy"], random_seed=data["random_seed"])
        model.class_prior_ = data["class_prior"]
        model.feature_names = data.get("feature_names", [])
        model.is_fitted = data.get("is_fitted", True)
        return model
