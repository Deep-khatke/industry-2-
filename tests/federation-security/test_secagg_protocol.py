"""Security tests for SecAgg+ protocol verification, dropout resilience, and threshold abort."""

import numpy as np
import pytest

from fcs_pfl.aggregation.secagg import SecAggConfig, SecAggProtocolSimulator


@pytest.fixture
def dummy_client_updates() -> dict:
    np.random.seed(42)
    return {
        f"isp_{i:02d}": [
            np.random.randn(64, 14).astype(np.float32),
            np.random.randn(64).astype(np.float32),
        ]
        for i in range(1, 8)
    }


def test_secagg_zero_dropout(dummy_client_updates: dict) -> None:
    sim = SecAggProtocolSimulator(SecAggConfig(num_participants=7, reconstruction_threshold=5))
    aggregated, meta = sim.simulate_aggregation(dummy_client_updates, dropped_clients=[])
    assert meta["status"] == "COMPLETED"
    assert meta["num_active"] == 7
    assert aggregated is not None
    assert len(aggregated) == 2


def test_secagg_one_dropout(dummy_client_updates: dict) -> None:
    sim = SecAggProtocolSimulator(SecAggConfig(num_participants=7, reconstruction_threshold=5))
    aggregated, meta = sim.simulate_aggregation(dummy_client_updates, dropped_clients=["isp_03"])
    assert meta["status"] == "COMPLETED"
    assert meta["num_active"] == 6
    assert aggregated is not None


def test_secagg_two_dropouts_at_threshold(dummy_client_updates: dict) -> None:
    # 7 - 2 = 5 == threshold k
    sim = SecAggProtocolSimulator(SecAggConfig(num_participants=7, reconstruction_threshold=5))
    aggregated, meta = sim.simulate_aggregation(dummy_client_updates, dropped_clients=["isp_01", "isp_07"])
    assert meta["status"] == "COMPLETED"
    assert meta["num_active"] == 5
    assert aggregated is not None


def test_secagg_below_threshold_must_abort_no_fallback(dummy_client_updates: dict) -> None:
    # 7 - 3 = 4 < threshold 5 -> MUST abort! Plaintext fallback strictly prohibited!
    sim = SecAggProtocolSimulator(SecAggConfig(num_participants=7, reconstruction_threshold=5))
    aggregated, meta = sim.simulate_aggregation(dummy_client_updates, dropped_clients=["isp_01", "isp_02", "isp_03"])
    assert meta["status"] == "ABORTED_BELOW_THRESHOLD"
    assert aggregated is None


def test_secagg_quantization_bounded_error(dummy_client_updates: dict) -> None:
    sim = SecAggProtocolSimulator(SecAggConfig(clipping_range=8.0, quantization_range=4194304))
    err = sim.measure_quantization_error(dummy_client_updates["isp_01"])
    # Quantization error must be small (< 1e-4)
    assert err["max_abs_error"] < 1e-4
    assert err["rmse"] < 1e-5
