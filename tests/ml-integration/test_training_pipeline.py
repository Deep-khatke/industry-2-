"""Integration tests for the end-to-end FCS Phase 3 ML training and registry pipeline."""

import tempfile
from pathlib import Path

import pytest

from fcs_ml.data.loader import DatasetLoader
from fcs_ml.export.exporter import ModelExporter
from fcs_ml.features.selector import FeatureSelector, FeatureTrack
from fcs_ml.registry.registry import CandidateModelRegistry
from fcs_ml.training.trainer import ModelTrainer


@pytest.mark.ml_integration
class TestTrainingPipelineE2E:
    """Validate end-to-end dataset loading, model training, threshold tuning, and artifact registration."""

    def test_e2e_binary_training_and_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            registry = CandidateModelRegistry(registry_dir=Path(tmp_dir) / "models")
            loader = DatasetLoader()
            train_df, val_df, test_df = loader.load_splits()

            selector = FeatureSelector(track=FeatureTrack.RESEARCH_BENCHMARK)
            X_train, y_train, _, f_names = selector.extract_matrices(train_df)
            X_val, y_val, _, _ = selector.extract_matrices(val_df, f_names)
            X_test, y_test, _, _ = selector.extract_matrices(test_df, f_names)

            trainer = ModelTrainer(registry=registry)
            model, manifest, metrics = trainer.train_and_evaluate(
                model_family="LightGBM",
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                X_test=X_test,
                y_test=y_test,
                feature_names=f_names,
                track=FeatureTrack.RESEARCH_BENCHMARK,
                model_params={"n_estimators": 15, "max_depth": 3},
            )

            assert manifest.model_id == "lightgbm_research_benchmark"
            assert "f1" in metrics
            assert metrics["f1"] > 0.0

            # Reload model from registry
            loaded_model, loaded_manifest = registry.load_model("lightgbm_research_benchmark")
            assert loaded_manifest.validation_threshold == manifest.validation_threshold

            orig_proba = model.predict_proba(X_test[:10])
            loaded_proba = loaded_model.predict_proba(X_test[:10])
            assert (abs(orig_proba - loaded_proba) < 1e-4).all()

            # Export model bundle
            export_info = ModelExporter.export_model(
                loaded_model,
                loaded_manifest,
                Path(tmp_dir) / "exports",
            )
            assert len(export_info["bundle_digest"]) == 64
            assert Path(export_info["manifest_file"]).exists()

    def test_e2e_deployable_track_training(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            registry = CandidateModelRegistry(registry_dir=Path(tmp_dir) / "models")
            loader = DatasetLoader()
            train_df, val_df, test_df = loader.load_splits()

            selector = FeatureSelector(track=FeatureTrack.DEPLOYABLE_SUBSET)
            X_train, y_train, _, f_names = selector.extract_matrices(train_df)
            X_val, y_val, _, _ = selector.extract_matrices(val_df, f_names)
            X_test, y_test, _, _ = selector.extract_matrices(test_df, f_names)

            trainer = ModelTrainer(registry=registry)
            model, manifest, metrics = trainer.train_and_evaluate(
                model_family="LogisticRegression",
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                X_test=X_test,
                y_test=y_test,
                feature_names=f_names,
                track=FeatureTrack.DEPLOYABLE_SUBSET,
            )
            assert manifest.feature_track == "DEPLOYABLE_SUBSET"
            assert len(f_names) <= 14  # FlowEvent v1 deployable parity
            assert "f1" in metrics
