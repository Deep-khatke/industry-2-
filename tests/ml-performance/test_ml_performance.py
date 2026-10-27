"""Performance and latency benchmark tests for FCS Phase 3 ML."""

import time

import numpy as np
import pytest

from fcs_ml.models.lightgbm_model import LightGBMModel
from fcs_ml.models.logistic import LogisticRegressionModel


@pytest.mark.ml_performance
class TestMLPerformance:
    """Validate CPU latency budgets, throughput, and model loading performance."""

    def test_single_flow_latency_under_50ms(self) -> None:
        rng = np.random.default_rng(42)
        X_train = rng.normal(size=(50, 10)).astype(np.float32)
        y_train = (X_train[:, 0] > 0).astype(np.int64)

        model = LightGBMModel(n_estimators=15, max_depth=4)
        model.fit(X_train, y_train, feature_names=[f"f{i}" for i in range(10)])

        single_sample = rng.normal(size=(1, 10)).astype(np.float32)

        # Warmup
        for _ in range(5):
            _ = model.predict_proba(single_sample)

        latencies_ms = []
        for _ in range(25):
            t0 = time.perf_counter()
            _ = model.predict_proba(single_sample)
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)

        p95_latency = float(np.percentile(latencies_ms, 95))
        # Operational requirement: p95 must be well below 50.0 ms
        assert p95_latency < 50.0

    def test_batch_throughput_flows_per_second(self) -> None:
        rng = np.random.default_rng(42)
        X = rng.normal(size=(64, 10)).astype(np.float32)
        y = (X[:, 0] > 0).astype(np.int64)

        model = LogisticRegressionModel()
        model.fit(X, y, feature_names=[f"f{i}" for i in range(10)])

        t0 = time.perf_counter()
        for _ in range(10):
            _ = model.predict_proba(X)
        total_time = time.perf_counter() - t0

        total_flows = 64 * 10
        throughput = total_flows / total_time
        # Logistic Regression should easily process thousands of flows per second
        assert throughput > 1000.0
