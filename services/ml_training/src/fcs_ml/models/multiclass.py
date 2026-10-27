"""Multiclass attack taxonomy classifier with uncertainty rejection mechanism."""

import hashlib
import json
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np

from .base import BaseFCSModel


class MulticlassAttackClassifier(BaseFCSModel):
    """Multiclass attack classifier mapping flow features to canonical taxonomy categories."""

    def __init__(
        self,
        n_estimators: int = 150,
        learning_rate: float = 0.05,
        num_leaves: int = 31,
        max_depth: int = 6,
        uncertainty_threshold: float = 0.40,
        random_seed: int = 42,
    ) -> None:
        super().__init__("MulticlassAttackClassifier", random_seed)
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.max_depth = max_depth
        self.uncertainty_threshold = uncertainty_threshold
        self.classes_: list[str] = []
        self.class_to_idx: dict[str, int] = {}
        self.idx_to_class: dict[int, str] = {}
        self._clf: lgb.LGBMClassifier | None = None

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        feature_names: list[str] | None = None,
    ) -> "MulticlassAttackClassifier":
        self.feature_names = feature_names or [f"f_{i}" for i in range(X_train.shape[1])]

        # Identify unique classes in training data
        unique_classes = sorted({str(c) for c in y_train})
        self.classes_ = unique_classes
        self.class_to_idx = {c: i for i, c in enumerate(self.classes_)}
        self.idx_to_class = dict(enumerate(self.classes_))

        y_train_idx = np.array([self.class_to_idx[str(c)] for c in y_train], dtype=np.int64)

        eval_set: list[tuple[np.ndarray, np.ndarray]] | None = None
        callbacks: list[Any] = []

        if X_val is not None and y_val is not None and len(X_val) > 0:
            y_val_idx = np.array([self.class_to_idx.get(str(c), 0) for c in y_val], dtype=np.int64)
            eval_set = [(X_val, y_val_idx)]
            callbacks.append(lgb.early_stopping(stopping_rounds=15, verbose=False))

        self._clf = lgb.LGBMClassifier(
            objective="multiclass",
            num_class=len(self.classes_),
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            num_leaves=self.num_leaves,
            max_depth=self.max_depth,
            class_weight="balanced",
            n_jobs=2,
            random_state=self.random_seed,
            verbosity=-1,
        )

        eval_set_data: Any = eval_set
        self._clf.fit(X_train, y_train_idx, eval_set=eval_set_data, callbacks=callbacks)
        self._booster = self._clf.booster_
        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet.")
        if hasattr(self, "_booster") and self._booster is not None:
            return np.asarray(self._booster.predict(X), dtype=np.float64)
        if self._clf is not None:
            return np.asarray(self._clf.predict_proba(X), dtype=np.float64)
        raise RuntimeError("No estimator or booster available.")

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Predict integer class indices."""
        proba = self.predict_proba(X)
        return np.argmax(proba, axis=1)

    def predict_labels(self, X: np.ndarray) -> list[dict[str, Any]]:
        """
        Predict string category names along with uncertainty/abstention flags.
        If max probability < uncertainty_threshold, flags as 'UNCERTAIN'.
        """
        proba = self.predict_proba(X)
        results = []
        for p_row in proba:
            best_idx = int(np.argmax(p_row))
            best_prob = float(p_row[best_idx])
            best_class = self.idx_to_class.get(best_idx, "Unknown")
            is_uncertain = best_prob < self.uncertainty_threshold
            results.append({
                "predicted_class": "Uncertain" if is_uncertain else best_class,
                "confidence": best_prob,
                "is_uncertain": is_uncertain,
                "raw_candidate": best_class,
            })
        return results

    def get_params(self) -> dict[str, Any]:
        return {
            "model_family": "MulticlassAttackClassifier",
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "num_leaves": self.num_leaves,
            "max_depth": self.max_depth,
            "uncertainty_threshold": self.uncertainty_threshold,
            "num_classes": len(self.classes_),
            "classes": self.classes_,
            "random_seed": self.random_seed,
        }

    def save(self, filepath: Path | str) -> str:
        if not self.is_fitted or self._clf is None:
            raise RuntimeError("Cannot save unfitted multiclass model.")
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
            "model_family": "MulticlassAttackClassifier",
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "num_leaves": self.num_leaves,
            "max_depth": self.max_depth,
            "uncertainty_threshold": self.uncertainty_threshold,
            "classes": self.classes_,
            "class_to_idx": self.class_to_idx,
            "feature_names": self.feature_names,
            "random_seed": self.random_seed,
            "is_fitted": self.is_fitted,
        }
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        combined_bytes = txt_path.read_bytes() + meta_path.read_bytes()
        return hashlib.sha256(combined_bytes).hexdigest()

    @classmethod
    def load(cls, filepath: Path | str) -> "MulticlassAttackClassifier":
        p = Path(filepath)
        txt_path = p.with_suffix(".txt")
        meta_path = p.with_suffix(".json")

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        model = cls(
            n_estimators=meta["n_estimators"],
            learning_rate=meta["learning_rate"],
            num_leaves=meta["num_leaves"],
            max_depth=meta["max_depth"],
            uncertainty_threshold=meta["uncertainty_threshold"],
            random_seed=meta["random_seed"],
        )
        model.classes_ = meta["classes"]
        model.class_to_idx = meta["class_to_idx"]
        model.idx_to_class = {int(v): k for k, v in model.class_to_idx.items()}
        model.feature_names = meta.get("feature_names", [])

        booster = lgb.Booster(model_file=str(txt_path))
        model._booster = booster
        model._clf = lgb.LGBMClassifier()
        model._clf._Booster = booster
        model._clf._n_classes = len(model.classes_)
        model._clf._classes = np.arange(len(model.classes_))
        model.is_fitted = True
        return model
