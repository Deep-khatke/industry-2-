"""Model trainer orchestrating training loops, threshold tuning, and model evaluation."""

import time
from typing import Any

import numpy as np

from fcs_ml.calibration.calibrator import ProbabilityCalibrator
from fcs_ml.evaluation.metrics import (
    compute_binary_metrics,
    compute_multiclass_metrics,
)
from fcs_ml.features.selector import FeatureSelector, FeatureTrack
from fcs_ml.models.base import BaseFCSModel
from fcs_ml.models.baseline import DummyBaselineClassifier
from fcs_ml.models.lightgbm_model import LightGBMModel
from fcs_ml.models.logistic import LogisticRegressionModel
from fcs_ml.models.mlp import PyTorchMLPModel
from fcs_ml.models.multiclass import MulticlassAttackClassifier
from fcs_ml.registry.manifest import ModelManifest
from fcs_ml.registry.registry import CandidateModelRegistry
from fcs_ml.thresholds.optimizer import ThresholdOptimizer


class ModelTrainer:
    """Orchestrates candidate model training, validation-based threshold optimization, and registration."""

    def __init__(
        self,
        registry: CandidateModelRegistry | None = None,
        random_seed: int = 42,
    ) -> None:
        self.registry = registry or CandidateModelRegistry()
        self.random_seed = random_seed

    def create_model(
        self,
        model_family: str,
        params: dict[str, Any] | None = None,
    ) -> BaseFCSModel:
        """Instantiate candidate model by family name."""
        p = params or {}
        fam = model_family.lower()

        if fam in ("dummy", "baseline", "dummybaseline"):
            return DummyBaselineClassifier(
                strategy=p.get("strategy", "prior"),
                random_seed=self.random_seed,
            )
        elif fam in ("logistic", "logisticregression"):
            return LogisticRegressionModel(
                C=p.get("C", 1.0),
                max_iter=p.get("max_iter", 1000),
                class_weight=p.get("class_weight", "balanced"),
                random_seed=self.random_seed,
            )
        elif fam in ("lightgbm", "lgbm"):
            return LightGBMModel(
                n_estimators=p.get("n_estimators", 150),
                learning_rate=p.get("learning_rate", 0.05),
                num_leaves=p.get("num_leaves", 31),
                max_depth=p.get("max_depth", 6),
                class_weight=p.get("class_weight", "balanced"),
                random_seed=self.random_seed,
            )
        elif fam in ("mlp", "pytorchmlp"):
            return PyTorchMLPModel(
                hidden_dims=p.get("hidden_dims", [128, 64]),
                dropout_rate=p.get("dropout_rate", 0.2),
                learning_rate=p.get("learning_rate", 0.001),
                batch_size=p.get("batch_size", 64),
                epochs=p.get("epochs", 25),
                random_seed=self.random_seed,
            )
        elif fam in ("multiclass", "multiclassclassifier"):
            return MulticlassAttackClassifier(
                n_estimators=p.get("n_estimators", 150),
                learning_rate=p.get("learning_rate", 0.05),
                uncertainty_threshold=p.get("uncertainty_threshold", 0.40),
                random_seed=self.random_seed,
            )
        else:
            raise ValueError(f"Unknown model family: {model_family}")

    def train_and_evaluate(
        self,
        model_family: str,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
        feature_names: list[str],
        track: FeatureTrack = FeatureTrack.RESEARCH_BENCHMARK,
        dataset_digest: str = "unknown",
        model_params: dict[str, Any] | None = None,
        optimize_threshold: bool = True,
        calibrate: bool = True,
    ) -> tuple[BaseFCSModel, ModelManifest, dict[str, Any]]:
        """
        Execute full training, validation threshold optimization, probability calibration,
        and held-out test evaluation.
        """
        model = self.create_model(model_family, model_params)

        # 1. Fit Model on Training split only
        start_t = time.perf_counter()
        model.fit(
            X_train,
            y_train,
            X_val=X_val,
            y_val=y_val,
            feature_names=feature_names,
        )
        training_time = time.perf_counter() - start_t

        is_multiclass = isinstance(model, MulticlassAttackClassifier)

        val_threshold = 0.5
        calibrator_info = {"method": "none"}

        if not is_multiclass:
            # 2. Validation predictions
            val_proba = model.predict_proba(X_val)

            # 3. Validation-only threshold optimization
            if optimize_threshold:
                opt = ThresholdOptimizer(objective="f1")
                opt.fit(y_val, val_proba)
                val_threshold = opt.optimal_threshold_

            # 4. Optional Probability Calibration on Validation
            if calibrate:
                cal = ProbabilityCalibrator(method="sigmoid")
                cal.fit(y_val, val_proba)
                calibrator_info = cal.get_info()

            # 5. Held-Out Evaluation on Test Partition
            test_proba = model.predict_proba(X_test)
            test_metrics = compute_binary_metrics(y_test, test_proba, threshold=val_threshold)
        else:
            # Multiclass evaluation
            test_preds = model.predict(X_test)
            test_proba = model.predict_proba(X_test)
            test_metrics = compute_multiclass_metrics(
                y_test,
                test_preds,
                y_prob=test_proba,
                class_names=getattr(model, "classes_", None),
            )

        test_metrics["training_time_seconds"] = training_time

        # 6. Build Manifest
        model_id = f"{model.model_name.lower()}_{track.value.lower()}"
        selector = FeatureSelector(track=track)
        schema_digest = selector.compute_feature_digest(feature_names)

        manifest = ModelManifest(
            model_id=model_id,
            model_family=model.model_name,
            feature_track=track.value,
            feature_schema_digest=schema_digest,
            feature_names=feature_names,
            dataset_manifest_digest=dataset_digest,
            training_sample_count=len(X_train),
            validation_sample_count=len(X_val),
            test_sample_count=len(X_test),
            validation_threshold=val_threshold,
            calibration_method=calibrator_info.get("method", "none"),
            test_metrics=test_metrics,
            artifact_hash="pending",
            artifact_path="pending",
        )

        # 7. Register Model in Candidate Registry
        self.registry.register_model(model, manifest)

        return model, manifest, test_metrics
