"""Security, adversarial input, and leakage prevention tests for FCS Phase 3 ML."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from fcs_ml.features.selector import FeatureSelector, TargetLeakageError
from fcs_ml.inference.engine import InferenceEngine
from fcs_ml.models.logistic import LogisticRegressionModel
from fcs_ml.registry.manifest import ModelManifest
from fcs_ml.registry.registry import CandidateModelRegistry
from fcs_ml.security.validator import MLSecurityError, MLSecurityValidator


@pytest.mark.ml_security
class TestMLSecurityAndDefense:
    """Validate zero-trust ML security, anti-leakage guards, and artifact integrity."""

    def test_prohibited_predictor_columns_rejected(self) -> None:
        selector = FeatureSelector()
        prohibited_cases = [
            ["IN_BYTES", "Attack"],
            ["IN_BYTES", "Label"],
            ["IN_BYTES", "canonical_attack_label"],
            ["IN_BYTES", "binary_label"],
            ["IN_BYTES", "dataset_source"],
            ["IN_BYTES", "isp_client_id"],
            ["IN_BYTES", "split_id"],
        ]
        for candidate in prohibited_cases:
            with pytest.raises(TargetLeakageError):
                selector.validate_features(candidate)

    def test_tampered_model_artifact_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            reg = CandidateModelRegistry(registry_dir=Path(tmp_dir))
            model = LogisticRegressionModel(C=1.0)
            X = np.array([[1.0, 2.0], [3.0, 4.0]])
            y = np.array([0, 1])
            model.fit(X, y, feature_names=["f0", "f1"])

            manifest = ModelManifest(
                model_id="test_tamper_model",
                model_family="LogisticRegression",
                feature_track="RESEARCH_BENCHMARK",
                feature_schema_digest="digest123",
                feature_names=["f0", "f1"],
                dataset_manifest_digest="ds123",
                training_sample_count=2,
                validation_sample_count=0,
                test_sample_count=0,
                artifact_hash="pending",
                artifact_path="pending",
            )
            reg.register_model(model, manifest)

            # Verification passes initially
            check1 = reg.verify_model_artifact("test_tamper_model")
            assert check1["integrity_verified"] is True

            # Deliberately tamper with the saved JSON artifact on disk
            art_file = Path(tmp_dir) / "test_tamper_model" / "model.json"
            art_file.write_text(art_file.read_text(encoding="utf-8") + " ", encoding="utf-8")

            # Verification must fail
            check2 = reg.verify_model_artifact("test_tamper_model")
            assert check2["integrity_verified"] is False

    def test_malformed_inputs_rejected(self) -> None:
        # NaN input
        bad_x_nan = np.array([[1.0, np.nan, 3.0]])
        with pytest.raises(MLSecurityError):
            MLSecurityValidator.validate_inference_inputs(bad_x_nan, expected_dim=3)

        # Inf input
        bad_x_inf = np.array([[1.0, np.inf, 3.0]])
        with pytest.raises(MLSecurityError):
            MLSecurityValidator.validate_inference_inputs(bad_x_inf, expected_dim=3)

        # Dimension mismatch
        bad_x_dim = np.array([[1.0, 2.0]])
        with pytest.raises(MLSecurityError):
            MLSecurityValidator.validate_inference_inputs(bad_x_dim, expected_dim=5)

    def test_inference_cannot_trigger_network_action(self) -> None:
        engine = InferenceEngine()
        res = engine.score_record(
            {"L4_SRC_PORT": 80, "L4_DST_PORT": 443, "PROTOCOL": 6, "IN_BYTES": 100},
            model_id="logisticregression_deployable_subset",
        )
        assert res.network_action_executed is False

    def test_unregistered_model_fails_safely(self) -> None:
        engine = InferenceEngine()
        with pytest.raises(FileNotFoundError):
            engine.score_record({"IN_BYTES": 100}, model_id="non_existent_model_id_xyz")
