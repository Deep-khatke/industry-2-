"""Unit tests for ConditionalModelRouter."""

import pytest

from fcs_ml.hmd.router import ConditionalModelRouter
from packages.contracts.model_score import ModelScore, ModelType


@pytest.fixture
def router():
    return ConditionalModelRouter(
        general_routing_threshold=0.35,
        anomaly_routing_threshold=0.40,
        enable_ddos_specialist=True,
        enable_scanning_specialist=True,
        enable_botnet_specialist=False,
    )


def test_benign_traffic_short_circuit(router):
    # Both general and anomaly detectors report low benign probability
    gen_score = ModelScore(
        model_id="gen",
        model_type=ModelType.GENERAL_DETECTOR,
        calibrated_probability=0.08,
        prediction=0,
    )
    anom_score = ModelScore(
        model_id="anom",
        model_type=ModelType.ANOMALY_DETECTOR,
        calibrated_probability=0.12,
        prediction=0,
    )
    normal_features = {
        "IN_BYTES": 1500,
        "IN_PKTS": 10,
        "TCP_FLAGS": 16,  # ACK
        "L4_DST_PORT": 443,
        "FLOW_DURATION_MILLISECONDS": 200,
    }

    decision = router.route(normal_features, gen_score, anom_score)
    assert decision.should_route_specialists is False
    assert len(decision.routed_models) == 0
    assert "ddos_specialist" in decision.bypassed_models
    assert "scanning_specialist" in decision.bypassed_models
    assert decision.routing_latency_us > 0.0


def test_volumetric_burst_routes_ddos(router):
    gen_score = ModelScore(
        model_id="gen",
        model_type=ModelType.GENERAL_DETECTOR,
        calibrated_probability=0.45,
        prediction=1,
    )
    anom_score = ModelScore(
        model_id="anom",
        model_type=ModelType.ANOMALY_DETECTOR,
        calibrated_probability=0.55,
        prediction=1,
    )
    burst_features = {
        "IN_BYTES": 850_000,
        "IN_PKTS": 3_500,
        "TCP_FLAGS": 24,
        "L4_DST_PORT": 80,
        "FLOW_DURATION_MILLISECONDS": 50,
    }

    decision = router.route(burst_features, gen_score, anom_score, flow_count=60)
    assert decision.should_route_specialists is True
    assert "ddos_specialist" in decision.routed_models
    assert any("VOLUMETRIC" in r for r in decision.trigger_reasons)


def test_syn_scan_routes_scanning_specialist(router):
    gen_score = ModelScore(
        model_id="gen",
        model_type=ModelType.GENERAL_DETECTOR,
        calibrated_probability=0.20,
        prediction=0,
    )
    anom_score = ModelScore(
        model_id="anom",
        model_type=ModelType.ANOMALY_DETECTOR,
        calibrated_probability=0.42,
        prediction=1,
    )
    scan_features = {
        "IN_BYTES": 120,
        "IN_PKTS": 2,
        "TCP_FLAGS": 2,  # SYN only
        "L4_DST_PORT": 23,  # Telnet probe
        "FLOW_DURATION_MILLISECONDS": 10,
    }

    decision = router.route(scan_features, gen_score, anom_score)
    assert decision.should_route_specialists is True
    assert "scanning_specialist" in decision.routed_models
