"""LightGBM tabular gradient boosted decision tree classifier."""

import hashlib
import json
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np

from .base import BaseFCSModel


class LightGBMModel(BaseFCSModel):
    """CPU-bounded LightGBM binary classifier with early stopping and feature importance."""

    def __init__(
        self,
        n_estimators: int = 150,
        learning_rate: float = 0.05,
        num_leaves: int = 31,
        max_depth: int = 6,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        class_weight: str | None = "balanced",
        n_jobs: int = 2,
        random_seed: int = 42,
    ) -> None:
        super().__init__("LightGBM", random_seed)
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.max_depth = max_depth
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.class_weight = class_weight
        self.n_jobs = n_jobs
        self._clf = lgb.LGBMClassifier(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            num_leaves=self.num_leaves,
            max_depth=self.max_depth,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            class_weight=self.class_weight,
            n_jobs=self.n_jobs,
            random_state=self.random_seed,
            verbosity=-1,
        )
        self.best_iteration_: int = 0
        self.feature_importances_: np.ndarray | None = None

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        feature_names: list[str] | None = None,
    ) -> "LightGBMModel":
        self.feature_names = feature_names or [f"f_{i}" for i in range(X_train.shape[1])]

        callbacks: list[Any] = []
        eval_set: list[tuple[np.ndarray, np.ndarray]] | None = None

        if X_val is not None and y_val is not None and len(X_val) > 0:
            eval_set = [(X_val, y_val)]
            callbacks.append(lgb.early_stopping(stopping_rounds=15, verbose=False))

        eval_set_data: Any = eval_set
        self._clf.fit(
            X_train,
            y_train,
            eval_set=eval_set_data,
            callbacks=callbacks,
        )

        self.best_iteration_ = getattr(self._clf, "best_iteration_", self.n_estimators)
        self.feature_importances_ = self._clf.feature_importances_
        self._booster = self._clf.booster_
        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet.")
        if hasattr(self, "_booster") and self._booster is not None:
            raw_p = np.asarray(self._booster.predict(X), dtype=np.float64)
            if raw_p.ndim == 1:
                return np.column_stack([1.0 - raw_p, raw_p])
            return raw_p
        proba = np.asarray(self._clf.predict_proba(X), dtype=np.float64)
        if proba.shape[1] == 1:
            other = 1.0 - proba
            return np.column_stack([other, proba])
        return proba

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        proba = self.predict_proba(X)
        return (proba[:, 1] >= threshold).astype(np.int64)

    def get_feature_importances(self) -> dict[str, float]:
        """Return mapping from feature name to split importance."""
        if self.feature_importances_ is None:
            return {}
        return dict(zip(self.feature_names, [float(x) for x in self.feature_importances_], strict=False))

    def get_params(self) -> dict[str, Any]:
        return {
            "model_family": "LightGBM",
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "num_leaves": self.num_leaves,
            "max_depth": self.max_depth,
            "subsample": self.subsample,
            "colsample_bytree": self.colsample_bytree,
            "class_weight": self.class_weight,
            "n_jobs": self.n_jobs,
            "random_seed": self.random_seed,
            "best_iteration": self.best_iteration_,
        }

    def save(self, filepath: Path | str) -> str:
        """Save model using native LightGBM text model representation and sidecar metadata JSON."""
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)

        txt_path = p.with_suffix(".txt")
        meta_path = p.with_suffix(".json")

        booster = getattr(self, "_booster", None)
        if booster is None and hasattr(self._clf, "booster_"):
            booster = self._clf.booster_
        if booster is None:
            raise RuntimeError("No booster available to save.")
        booster.save_model(str(txt_path))

        meta = {
            "model_family": "LightGBM",
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "num_leaves": self.num_leaves,
            "max_depth": self.max_depth,
            "subsample": self.subsample,
            "colsample_bytree": self.colsample_bytree,
            "class_weight": self.class_weight,
            "random_seed": self.random_seed,
            "feature_names": self.feature_names,
            "best_iteration": self.best_iteration_,
            "is_fitted": self.is_fitted,
        }
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        # Combine text model and metadata to compute deterministic SHA-256
        combined_bytes = txt_path.read_bytes() + meta_path.read_bytes()
        return hashlib.sha256(combined_bytes).hexdigest()

    @classmethod
    def load(cls, filepath: Path | str) -> "LightGBMModel":
        p = Path(filepath)
        txt_path = p.with_suffix(".txt")
        meta_path = p.with_suffix(".json")

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        model = cls(
            n_estimators=meta["n_estimators"],
            learning_rate=meta["learning_rate"],
            num_leaves=meta["num_leaves"],
            max_depth=meta["max_depth"],
            subsample=meta["subsample"],
            colsample_bytree=meta["colsample_bytree"],
            class_weight=meta["class_weight"],
            random_seed=meta["random_seed"],
        )
        model.feature_names = meta.get("feature_names", [])
        model.best_iteration_ = meta.get("best_iteration", 0)
        model.is_fitted = meta.get("is_fitted", True)

        booster = lgb.Booster(model_file=str(txt_path))
        model._booster = booster
        model._clf._Booster = booster
        model._clf._n_classes = 2
        model._clf._classes = np.array([0, 1])
        model.feature_importances_ = booster.feature_importance()
        return model
