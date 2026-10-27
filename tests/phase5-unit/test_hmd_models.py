"""Unit tests for Phase 5 Anomaly and Specialist models."""

import numpy as np
import pytest

from fcs_ml.models.autoencoder import AutoencoderAnomalyModel
from fcs_ml.models.botnet_specialist import assess_botnet_eligibility
from fcs_ml.models.ddos_specialist import DDoSSpecialistModel
from fcs_ml.models.isolation_forest import IsolationForestAnomalyModel
from fcs_ml.models.scanning_specialist import ScanningSpecialistModel


@pytest.fixture
def synthetic_features():
    rng = np.random.RandomState(42)
    # 50 samples, 9 features
    X_benign = rng.normal(loc=10.0, scale=2.0, size=(50, 9)).astype(np.float32)
    X_attack = rng.normal(loc=50.0, scale=10.0, size=(25, 9)).astype(np.float32)
    X = np.vstack([X_benign, X_attack])
    y = np.array([0] * 50 + [1] * 25, dtype=np.int64)
    feature_names = [
        "L4_SRC_PORT", "L4_DST_PORT", "PROTOCOL", "IN_BYTES", "IN_PKTS",
        "FLOW_DURATION_MILLISECONDS", "TCP_FLAGS", "SRC_TO_DST_SECOND_BYTES", "SRC_TO_DST_AVG_THROUGHPUT"
    ]
    return X, y, feature_names


def test_isolation_forest_anomaly_model(synthetic_features):
    X, y, feature_names = synthetic_features
    model = IsolationForestAnomalyModel(n_estimators=30, contamination=0.1, random_seed=42)
    model.fit(X, y_train=y, feature_names=feature_names)

    assert model.is_fitted is True
    assert len(model.feature_names) == 9

    proba = model.predict_proba(X)
    assert proba.shape == (len(X), 2)
    assert np.all(proba >= 0.0) and np.all(proba <= 1.0)
    assert np.allclose(np.sum(proba, axis=1), 1.0)

    preds = model.predict(X, threshold=0.5)
    assert len(preds) == len(X)
    assert set(preds).issubset({0, 1})


def test_autoencoder_anomaly_model(synthetic_features):
    X, y, feature_names = synthetic_features
    model = AutoencoderAnomalyModel(hidden_dim=8, latent_dim=4, epochs=5, random_seed=42)
    model.fit(X, y_train=y, feature_names=feature_names)

    assert model.is_fitted is True
    recon_err = model.reconstruction_error(X)
    assert len(recon_err) == len(X)
    assert np.all(recon_err >= 0.0)

    proba = model.predict_proba(X)
    assert proba.shape == (len(X), 2)
    assert np.all(proba >= 0.0) and np.all(proba <= 1.0)


def test_ddos_specialist_model(synthetic_features):
    X, y, feature_names = synthetic_features
    model = DDoSSpecialistModel(n_estimators=30, random_seed=42)
    model.fit(X, y, feature_names=feature_names)

    assert model.is_fitted is True
    proba = model.predict_proba(X)
    assert proba.shape == (len(X), 2)
    assert np.all(proba >= 0.0) and np.all(proba <= 1.0)


def test_scanning_specialist_model(synthetic_features):
    X, y, feature_names = synthetic_features
    model = ScanningSpecialistModel(n_estimators=30, random_seed=42)
    model.fit(X, y, feature_names=feature_names)

    assert model.is_fitted is True
    proba = model.predict_proba(X)
    assert proba.shape == (len(X), 2)
    assert np.all(proba >= 0.0) and np.all(proba <= 1.0)


def test_botnet_eligibility_assessment():
    deployable_features = [
        "L4_SRC_PORT", "L4_DST_PORT", "PROTOCOL", "IN_BYTES", "IN_PKTS",
        "FLOW_DURATION_MILLISECONDS", "TCP_FLAGS"
    ]
    res = assess_botnet_eligibility(deployable_features)
    assert res["is_eligible"] is False
    assert res["status"] == "NOT_ELIGIBLE_FOR_PRODUCTION_DEPLOYMENT"
    assert "DNS_QUERY_ID" in res["missing_prerequisites"]

    # Full research features with DNS payload
    research_features = deployable_features + ["DNS_QUERY_ID", "DNS_QUERY_TYPE", "DNS_TTL_ANSWER", "SRC_TO_DST_AVG_THROUGHPUT"]
    res_eligible = assess_botnet_eligibility(research_features)
    assert res_eligible["is_eligible"] is True
    assert res_eligible["status"] == "ELIGIBLE"
