"""Unit tests for candidate ML models: DummyBaseline, LogisticRegression, LightGBM, PyTorchMLP, Multiclass."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from fcs_ml.models.baseline import DummyBaselineClassifier
from fcs_ml.models.lightgbm_model import LightGBMModel
from fcs_ml.models.logistic import LogisticRegressionModel
from fcs_ml.models.mlp import PyTorchMLPModel
from fcs_ml.models.multiclass import MulticlassAttackClassifier


@pytest.fixture
def synthetic_binary_data() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(42)
    X_train = rng.normal(size=(80, 5)).astype(np.float32)
    y_train = (X_train[:, 0] + X_train[:, 1] > 0).astype(np.int64)
    X_val = rng.normal(size=(20, 5)).astype(np.float32)
    y_val = (X_val[:, 0] + X_val[:, 1] > 0).astype(np.int64)
    return X_train, y_train, X_val, y_val


@pytest.mark.ml_unit
class TestCandidateModels:
    """Validate fit, predict, predict_proba, save, and load for all candidate models."""

    def test_dummy_baseline(self, synthetic_binary_data: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]) -> None:
        X_train, y_train, X_val, y_val = synthetic_binary_data
        model = DummyBaselineClassifier(strategy="prior")
        model.fit(X_train, y_train)

        proba = model.predict_proba(X_val)
        preds = model.predict(X_val)
        assert proba.shape == (20, 2)
        assert len(preds) == 20

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_path = Path(tmp_dir) / "dummy.json"
            model.save(save_path)
            loaded = DummyBaselineClassifier.load(save_path)
            loaded_preds = loaded.predict(X_val)
            assert np.array_equal(preds, loaded_preds)

    def test_logistic_regression(self, synthetic_binary_data: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]) -> None:
        X_train, y_train, X_val, y_val = synthetic_binary_data
        model = LogisticRegressionModel(C=1.0)
        model.fit(X_train, y_train, X_val, y_val, feature_names=["f0", "f1", "f2", "f3", "f4"])

        proba = model.predict_proba(X_val)
        preds = model.predict(X_val)
        assert proba.shape == (20, 2)
        assert (proba >= 0.0).all() and (proba <= 1.0).all()
        assert len(preds) == 20

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_path = Path(tmp_dir) / "logistic.json"
            model.save(save_path)
            loaded = LogisticRegressionModel.load(save_path)
            loaded_proba = loaded.predict_proba(X_val)
            assert np.allclose(proba, loaded_proba, atol=1e-5)

    def test_lightgbm_model(self, synthetic_binary_data: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]) -> None:
        X_train, y_train, X_val, y_val = synthetic_binary_data
        model = LightGBMModel(n_estimators=10, max_depth=3)
        model.fit(X_train, y_train, X_val, y_val, feature_names=["f0", "f1", "f2", "f3", "f4"])

        proba = model.predict_proba(X_val)
        preds = model.predict(X_val)
        assert proba.shape == (20, 2)
        assert len(preds) == 20
        assert len(model.get_feature_importances()) == 5

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_path = Path(tmp_dir) / "lightgbm"
            model.save(save_path)
            loaded = LightGBMModel.load(save_path)
            loaded_proba = loaded.predict_proba(X_val)
            assert np.allclose(proba, loaded_proba, atol=1e-5)

    def test_pytorch_mlp_model(self, synthetic_binary_data: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]) -> None:
        X_train, y_train, X_val, y_val = synthetic_binary_data
        model = PyTorchMLPModel(hidden_dims=[32, 16], epochs=5, batch_size=16)
        model.fit(X_train, y_train, X_val, y_val, feature_names=["f0", "f1", "f2", "f3", "f4"])

        proba = model.predict_proba(X_val)
        preds = model.predict(X_val)
        assert proba.shape == (20, 2)
        assert len(preds) == 20

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_path = Path(tmp_dir) / "mlp"
            model.save(save_path)
            loaded = PyTorchMLPModel.load(save_path)
            loaded_proba = loaded.predict_proba(X_val)
            assert np.allclose(proba, loaded_proba, atol=1e-4)

    def test_multiclass_classifier(self) -> None:
        rng = np.random.default_rng(42)
        X_train = rng.normal(size=(90, 4)).astype(np.float32)
        y_train = np.array(["Benign"] * 30 + ["DoS"] * 30 + ["DDoS"] * 30)
        X_val = rng.normal(size=(30, 4)).astype(np.float32)
        y_val = np.array(["Benign"] * 10 + ["DoS"] * 10 + ["DDoS"] * 10)

        model = MulticlassAttackClassifier(n_estimators=10, max_depth=3)
        model.fit(X_train, y_train, X_val, y_val, feature_names=["f0", "f1", "f2", "f3"])

        proba = model.predict_proba(X_val)
        preds = model.predict(X_val)
        labels = model.predict_labels(X_val)

        assert proba.shape == (30, 3)
        assert len(preds) == 30
        assert len(labels) == 30
        assert "predicted_class" in labels[0]
        assert "confidence" in labels[0]

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_path = Path(tmp_dir) / "multiclass"
            model.save(save_path)
            loaded = MulticlassAttackClassifier.load(save_path)
            loaded_proba = loaded.predict_proba(X_val)
            assert np.allclose(proba, loaded_proba, atol=1e-5)
