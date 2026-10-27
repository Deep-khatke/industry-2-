"""Security and reliability boundary tests for FCS-HMD."""


from fcs_ml.hmd.executor import HierarchicalDetectionEngine
from packages.contracts.model_score import ModelType, ScoringStatus


def test_safety_invariant_network_action_executed_is_always_false():
    engine = HierarchicalDetectionEngine()
    win_data = {
        "window_id": "safety_check_win",
        "tenant_id": "rural-isp-alpha",
        "flow_count": 50,
        "feature_vector": {
            "L4_SRC_PORT": 80,
            "L4_DST_PORT": 80,
            "PROTOCOL": 6,
            "IN_BYTES": 1_000_000,
            "IN_PKTS": 5_000,
            "FLOW_DURATION_MILLISECONDS": 100.0,
            "TCP_FLAGS": 24,
            "SRC_TO_DST_SECOND_BYTES": 10_000_000.0,
            "SRC_TO_DST_AVG_THROUGHPUT": 10_000_000.0,
        },
    }
    evidence = engine.evaluate_window(win_data)
    assert evidence.network_action_executed is False
    assert evidence.general_score.network_action_executed is False
    assert evidence.anomaly_score.network_action_executed is False
    for s in evidence.specialist_scores:
        assert s.network_action_executed is False


def test_specialist_timeout_resilience():
    # If specialist execution takes longer than timeout budget, engine sets TIMEOUT and continues
    engine = HierarchicalDetectionEngine(specialist_timeout_us=0.0001)  # tiny budget forcing timeout
    win_data = {
        "window_id": "timeout_win",
        "tenant_id": "rural-isp-alpha",
        "flow_count": 50,
        "feature_vector": {
            "L4_SRC_PORT": 80,
            "L4_DST_PORT": 80,
            "PROTOCOL": 6,
            "IN_BYTES": 500_000,
            "IN_PKTS": 2_000,
            "FLOW_DURATION_MILLISECONDS": 100.0,
            "TCP_FLAGS": 2,
        },
    }
    evidence = engine.evaluate_window(win_data)
    # Pipeline should complete safely without raising an unhandled exception
    assert evidence.composite_risk >= 0.0
    assert evidence.network_action_executed is False


def test_missing_specialist_fallback():
    engine = HierarchicalDetectionEngine()
    # Inquire about a non-existent specialist
    missing_score = engine._execute_model_score(
        model_id="completely_non_existent_specialist",
        model_type=ModelType.DDOS_SPECIALIST,
        features={},
        tenant_id="rural-isp-alpha",
    )
    assert missing_score.status == ScoringStatus.MISSING
    assert missing_score.raw_score == -1.0
    assert missing_score.predicted_label == "UNKNOWN"
    assert missing_score.network_action_executed is False
