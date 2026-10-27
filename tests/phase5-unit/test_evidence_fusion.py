"""Unit tests for EvidenceFusionEngine."""

import pytest

from fcs_ml.hmd.fusion import EvidenceFusionEngine
from fcs_ml.hmd.router import RoutingDecision
from packages.contracts.model_score import ModelScore, ModelType


@pytest.fixture
def fusion_engine():
    return EvidenceFusionEngine()


def test_level1_benign_fusion(fusion_engine):
    gen = ModelScore(
        model_id="gen",
        model_type=ModelType.GENERAL_DETECTOR,
        calibrated_probability=0.10,
        prediction=0,
    )
    anom = ModelScore(
        model_id="anom",
        model_type=ModelType.ANOMALY_DETECTOR,
        calibrated_probability=0.08,
        prediction=0,
    )
    routing = RoutingDecision(
        tenant_id="alpha",
        level1_general_score=0.10,
        level1_anomaly_score=0.08,
        should_route_specialists=False,
        routed_models=[],
        bypassed_models=["ddos_specialist"],
    )

    fused = fusion_engine.fuse(gen, anom, [], [], routing)
    assert fused.composite_risk < 0.25
    assert fused.severity == "INFORMATIONAL"
    assert fused.is_threat is False
    assert fused.attack_category == "Benign"
    assert fused.network_action_executed is False


def test_specialist_dominance(fusion_engine):
    gen = ModelScore(
        model_id="gen",
        model_type=ModelType.GENERAL_DETECTOR,
        calibrated_probability=0.55,
        prediction=1,
    )
    anom = ModelScore(
        model_id="anom",
        model_type=ModelType.ANOMALY_DETECTOR,
        calibrated_probability=0.60,
        prediction=1,
    )
    ddos_spec = ModelScore(
        model_id="lightgbm_ddos_specialist",
        model_type=ModelType.DDOS_SPECIALIST,
        calibrated_probability=0.92,
        prediction=1,
        predicted_label="DDoS",
    )
    routing = RoutingDecision(
        tenant_id="alpha",
        level1_general_score=0.55,
        level1_anomaly_score=0.60,
        should_route_specialists=True,
        routed_models=["ddos_specialist"],
    )

    fused = fusion_engine.fuse(gen, anom, [ddos_spec], [], routing)
    assert fused.composite_risk >= 0.70
    assert fused.severity in ("HIGH", "CRITICAL")
    assert fused.attack_category == "DDoS"
    assert fused.is_threat is True
    assert fused.fusion_method == "SPECIALIST_DOMINANT"


def test_deterministic_rule_risk_floor(fusion_engine):
    gen = ModelScore(
        model_id="gen",
        model_type=ModelType.GENERAL_DETECTOR,
        calibrated_probability=0.20,
        prediction=0,
    )
    anom = ModelScore(
        model_id="anom",
        model_type=ModelType.ANOMALY_DETECTOR,
        calibrated_probability=0.15,
        prediction=0,
    )
    rule_matches = [
        {"rule_id": "FCS-R101", "name": "Volumetric Flood", "severity": "CRITICAL", "attack_category": "DDoS"}
    ]
    routing = RoutingDecision(
        tenant_id="alpha",
        level1_general_score=0.20,
        level1_anomaly_score=0.15,
        should_route_specialists=False,
    )

    fused = fusion_engine.fuse(gen, anom, [], rule_matches, routing)
    # Critical rule match enforces minimum risk floor of 0.95
    assert fused.composite_risk >= 0.95
    assert fused.severity == "CRITICAL"
    assert fused.is_threat is True
    assert "RULES_FLOOR" in fused.fusion_method


def test_missing_and_timeout_model_handling(fusion_engine):
    gen = ModelScore(
        model_id="gen",
        model_type=ModelType.GENERAL_DETECTOR,
        calibrated_probability=0.75,
        prediction=1,
    )
    # Anomaly detector timed out
    anom = ModelScore.timeout("anom", ModelType.ANOMALY_DETECTOR, budget_us=50000.0)
    # Specialist missing
    spec = ModelScore.missing("spec_ddos", ModelType.DDOS_SPECIALIST)

    routing = RoutingDecision(
        tenant_id="alpha",
        level1_general_score=0.75,
        level1_anomaly_score=0.0,
        should_route_specialists=True,
        routed_models=["spec_ddos"],
    )

    # Engine must not crash and must not fabricate benign scores for missing models
    fused = fusion_engine.fuse(gen, anom, [spec], [], routing)
    assert fused.fusion_method == "FALLBACK_GENERAL_ONLY"
    assert fused.composite_risk == 0.75
    assert fused.is_threat is True
    assert any("MODEL_DEGRADED" in r for r in fused.reason_codes)
