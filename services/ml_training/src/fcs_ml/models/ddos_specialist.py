"""DDoS Attack Specialist Model optimized for volumetric, SYN flood, and amplification traffic."""

import hashlib
import json
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np

from .base import BaseFCSModel


class DDoSSpecialistModel(BaseFCSModel):
    """
    Specialist classifier for high-volume, packet flood, and DDoS anomalies.
    Trained on verified DDoS subsets with volumetric feature weighting.
    """

    def __init__(
        self,
        n_estimators: int = 120,
        learning_rate: float = 0.05,
        num_leaves: int = 24,
        max_depth: int = 5,
        subsample: float = 0.85,
        colsample_bytree: float = 0.85,
        class_weight: str | None = "balanced",
        n_jobs: int = 2,
        random_seed: int = 42,
    ) -> None:
        super().__init__("DDoSSpecialist", random_seed)
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
    ) -> "DDoSSpecialistModel":
        self.feature_names = feature_names or []
        X_clean = np.nan_to_num(X_train, nan=0.0, posinf=1e6, neginf=-1e6)

        callbacks = [lgb.early_stopping(stopping_rounds=15, verbose=False)] if (X_val is not None and y_val is not None) else None
        eval_set = [(X_val, y_val)] if (X_val is not None and y_val is not None) else None

        self._clf.fit(
            X_clean,
            y_train,
            eval_set=eval_set,
            callbacks=callbacks,
        )
        self.is_fitted = True
        self.best_iteration_ = getattr(self._clf, "best_iteration_", 0) or 0
        self.feature_importances_ = self._clf.feature_importances_
        return self

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted.")
        proba = self.predict_proba(X)
        return (proba[:, 1] >= threshold).astype(np.int64)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted.")
        X_clean = np.nan_to_num(X, nan=0.0, posinf=1e6, neginf=-1e6)
        if hasattr(self, "_booster") and self._booster is not None:
            raw_p = np.asarray(self._booster.predict(X_clean), dtype=np.float64)
            if raw_p.ndim == 1:
                return np.column_stack([1.0 - raw_p, raw_p])
            return raw_p
        proba = self._clf.predict_proba(X_clean)
        if proba.ndim == 1:
            return np.vstack([1.0 - proba, proba]).T
        if proba.shape[1] == 1:
            p = proba[:, 0]
            return np.vstack([1.0 - p, p]).T
        return proba

    def get_params(self) -> dict[str, Any]:
        return {
            "model_family": "DDoSSpecialist",
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "num_leaves": self.num_leaves,
            "max_depth": self.max_depth,
            "subsample": self.subsample,
            "colsample_bytree": self.colsample_bytree,
            "class_weight": self.class_weight,
            "random_seed": self.random_seed,
            "best_iteration": self.best_iteration_,
        }

    def save(self, filepath: Path | str) -> str:
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
            "model_family": "DDoSSpecialist",
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

        combined = txt_path.read_bytes() + meta_path.read_bytes()
        return hashlib.sha256(combined).hexdigest()

    @classmethod
    def load(cls, filepath: Path | str) -> "DDoSSpecialistModel":
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
