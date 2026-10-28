"""Integration tests for Phase 9 Shadow Detection Pipeline and 7-Day Replay."""

import pytest
from datetime import UTC, datetime

from fcs_pilot.shadow_monitoring.engine import ShadowMonitoringEngine
from fcs_pilot.shadow_monitoring.seven_day_evaluator import SevenDayEvaluator


def test_shadow_detection_normal_telemetry():
    """Verify normal telemetry produces low anomaly scores and no candidate incidents."""
    engine = ShadowMonitoringEngine("rural-isp-alpha", shadow_mode_enabled=True)
    res = engine.process_telemetry_window("exp-01", {
        "src_ip": "10.0.1.15",
        "dst_ip": "192.168.1.20",
        "protocol": 6,
        "tcp_flags": 16,  # ACK
        "packet_count": 80,
        "byte_count": 24000,
    })
    assert res is None
    metrics = engine.get_metrics()
    assert metrics["total_flows_ingested"] == 80
    assert metrics["total_windows_scored"] == 1
    assert metrics["candidate_incidents_generated"] == 0
    assert metrics["network_action_executed"] is False


def test_shadow_detection_syn_flood_threat():
    """Verify suspected attack window triggers candidate incident with advisory recommendation."""
    engine = ShadowMonitoringEngine("rural-isp-alpha", shadow_mode_enabled=True)
    candidate = engine.process_telemetry_window("exp-01", {
        "src_ip": "198.51.100.33",
        "dst_ip": "192.168.1.100",
        "protocol": 6,
        "tcp_flags": 2,  # SYN only
        "packet_count": 6000,
        "byte_count": 240000,
    })
    assert candidate is not None
    assert candidate.attack_class == "SYN_FLOOD"
    assert candidate.anomaly_score >= 0.70
    assert candidate.is_shadow_mode is True
    assert candidate.action_executed is False  # Strict invariant

    # Check advisory recommendation
    rec = candidate.advisory_recommendation
    assert rec["action_type"] == "TEMPORARY_BLOCK"
    assert rec["target"] == "198.51.100.33"
    assert rec["execution_status"] == "ADVISORY_ONLY_NOT_EXECUTED"


def test_shadow_detection_model_offline_fallback():
    """Verify graceful fallback to rule heuristics when ML model throws exception."""
    engine = ShadowMonitoringEngine("rural-isp-alpha", shadow_mode_enabled=True)

    def crashing_model(w):
        raise RuntimeError("Inference worker terminated")

    candidate = engine.process_telemetry_window("exp-01", {
        "src_ip": "198.51.100.44",
        "dst_ip": "192.168.1.100",
        "protocol": 6,
        "tcp_flags": 2,
        "packet_count": 7500,
        "byte_count": 300000,
    }, model_score_fn=crashing_model)

    assert candidate is not None
    assert candidate.attack_class == "SYN_FLOOD"
    assert candidate.anomaly_score >= 0.70


def test_seven_day_shadow_evaluator_simulated_scenario():
    """Verify 7-day shadow evaluation simulation records all 7 days and computes averages."""
    evaluator = SevenDayEvaluator("pilot-sim-001", "rural-isp-alpha", is_simulation=True)
    report = evaluator.run_simulated_7_day_scenario()

    assert report.days_completed == 7
    assert report.total_flows_processed > 10_000_000
    assert report.total_candidate_incidents >= 10
    assert len(report.daily_records) == 7

    # Target compliance
    assert report.average_false_incidents_per_day <= 5.0
    assert report.target_met_le_5_false_per_day is True
    assert report.average_analyst_review_minutes_per_day <= 20.0
    assert report.analyst_capacity_target_met is True
    assert "SHADOW_EVALUATION_PASS" in report.recommendation
