"""Reproducibility and seed-invariance tests for FCS Phase 3 ML."""

import numpy as np
import pytest

from fcs_ml.models.lightgbm_model import LightGBMModel
from fcs_ml.models.logistic import LogisticRegressionModel
from fcs_ml.registry.manifest import ModelManifest


@pytest.mark.ml_reproducibility
class TestMLReproducibility:
    """Validate seed determinism, prediction invariance, and manifest digest stability."""

    def test_logistic_regression_seed_determinism(self) -> None:
        rng = np.random.default_rng(42)
        X = rng.normal(size=(50, 4)).astype(np.float32)
        y = (X[:, 0] > 0).astype(np.int64)

        m1 = LogisticRegressionModel(random_seed=42).fit(X, y, feature_names=["f0", "f1", "f2", "f3"])
        m2 = LogisticRegressionModel(random_seed=42).fit(X, y, feature_names=["f0", "f1", "f2", "f3"])

        p1 = m1.predict_proba(X)
        p2 = m2.predict_proba(X)
        assert np.array_equal(p1, p2)

    def test_lightgbm_seed_determinism(self) -> None:
        rng = np.random.default_rng(42)
        X = rng.normal(size=(50, 4)).astype(np.float32)
        y = (X[:, 0] > 0).astype(np.int64)

        m1 = LightGBMModel(n_estimators=10, random_seed=42).fit(X, y, feature_names=["f0", "f1", "f2", "f3"])
        m2 = LightGBMModel(n_estimators=10, random_seed=42).fit(X, y, feature_names=["f0", "f1", "f2", "f3"])

        p1 = m1.predict_proba(X)
        p2 = m2.predict_proba(X)
        assert np.allclose(p1, p2, atol=1e-5)

    def test_manifest_digest_stability(self) -> None:
        m = ModelManifest(
            model_id="test_model_digest",
            model_family="LightGBM",
            feature_track="RESEARCH_BENCHMARK",
            feature_schema_digest="digest_abc",
            feature_names=["f0", "f1"],
            dataset_manifest_digest="ds_digest_xyz",
            training_sample_count=100,
            validation_sample_count=20,
            test_sample_count=20,
            artifact_hash="hash123",
            artifact_path="artifacts/test",
            created_at="2026-10-25T12:00:00Z",
            git_commit="stable_commit",
        )
        d1 = m.compute_manifest_digest()
        d2 = m.compute_manifest_digest()
        assert d1 == d2
        assert len(d1) == 64
