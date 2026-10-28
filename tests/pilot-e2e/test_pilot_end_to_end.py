"""End-to-end tests for the complete Phase 9 ISP Pilot Lifecycle."""

import pytest
from datetime import UTC, datetime

from fcs_pilot.analyst_feedback.feedback_manager import AnalystFeedbackManager, IncidentDisposition
from fcs_pilot.exporter_compatibility.feature_parity import FeatureParityValidator
from fcs_pilot.exporter_compatibility.registry import ExporterCapabilityRegistry
from fcs_pilot.metrics.false_alert_meter import FalseAlertMeter
from fcs_pilot.onboarding.models import EnvironmentMode, NetworkScope, OnboardingStatus, PilotProfile
from fcs_pilot.onboarding.state_machine import OnboardingStateMachine
from fcs_pilot.readiness.gates_evaluator import PilotReadinessEvaluator
from fcs_pilot.response_validation.safety_validator import ResponseSafetyValidator
from fcs_pilot.shadow_monitoring.engine import ShadowMonitoringEngine
from fcs_pilot.shadow_monitoring.seven_day_evaluator import SevenDayEvaluator


def test_complete_pilot_lifecycle_e2e():
    """
    Execute full end-to-end simulated pilot workflow:
    Onboard -> Validate Exporter -> Shadow Detection -> Analyst Triage ->
    Manual Response -> Simulator Read-Back -> 7-Day Reporting -> Readiness Gate Audit.
    """
    # 1. Onboard simulated ISP profile
    profile = PilotProfile(
        pilot_id="pilot-e2e-001",
        tenant_id="rural-isp-alpha",
        isp_display_name="Northern Valley Broadband (ASN 64512)",
        environment_mode=EnvironmentMode.MODE_A_SYNTHETIC,
        status=OnboardingStatus.DRAFT,
        technical_contact="soc-lead@alpha-broadband.test",
        authorized_network_scope=NetworkScope(prefixes=["192.168.1.0/24"], observation_domain_ids=[1001]),
    )
    sm = OnboardingStateMachine([profile])

    # Walk through state machine
    sm.transition_state("pilot-e2e-001", OnboardingStatus.AUTHORIZATION_PENDING, "admin1", "PLATFORM_ADMIN", "Initialized")
    sm.transition_state("pilot-e2e-001", OnboardingStatus.TECHNICAL_REVIEW, "admin1", "PLATFORM_ADMIN", "Auth confirmed")
    sm.transition_state("pilot-e2e-001", OnboardingStatus.SECURITY_REVIEW, "admin1", "PLATFORM_ADMIN", "Tech review pass")
    sm.transition_state("pilot-e2e-001", OnboardingStatus.READY_FOR_SHADOW, "admin1", "PLATFORM_ADMIN", "Security pass")
    active_prof = sm.transition_state("pilot-e2e-001", OnboardingStatus.SHADOW_ACTIVE, "admin1", "PLATFORM_ADMIN", "Active")
    assert active_prof.status == OnboardingStatus.SHADOW_ACTIVE

    # 2. Exporter capability and feature parity validation
    cisco_prof = ExporterCapabilityRegistry.get_profile("cisco_asr")
    assert cisco_prof is not None
    parity_val = FeatureParityValidator()
    parity_res = parity_val.evaluate_parity("exp-e2e-01", cisco_prof.vendor, "IPFIX", cisco_prof.supported_fields)
    assert parity_res.parity_percentage > 50.0

    # 3. Server-enforced Shadow Detection
    shadow_eng = ShadowMonitoringEngine(profile.tenant_id, shadow_mode_enabled=True)

    # Ingest clean traffic
    shadow_eng.process_telemetry_window("exp-e2e-01", {
        "src_ip": "10.0.1.20", "dst_ip": "192.168.1.10", "protocol": 6,
        "tcp_flags": 16, "packet_count": 50, "byte_count": 12000,
    })

    # Ingest attack traffic (SYN flood)
    candidate = shadow_eng.process_telemetry_window("exp-e2e-01", {
        "src_ip": "198.51.100.99", "dst_ip": "192.168.1.100", "protocol": 6,
        "tcp_flags": 2, "packet_count": 5500, "byte_count": 220000,
    })
    assert candidate is not None
    assert candidate.attack_class == "SYN_FLOOD"
    assert candidate.action_executed is False

    # 4. Tier-1 Analyst Triage Feedback
    fb_mgr = AnalystFeedbackManager()
    fb_rec = fb_mgr.submit_feedback(
        incident_id=candidate.candidate_id,
        tenant_id=profile.tenant_id,
        analyst_id="analyst_alpha",
        analyst_role="SECURITY_ANALYST",
        disposition=IncidentDisposition.TRUE_POSITIVE,
        review_duration_seconds=145.0,
        notes="Verified volumetric SYN flood against target.",
    )
    assert fb_rec.disposition == IncidentDisposition.TRUE_POSITIVE

    # 5. Tier-2 Security Responder Manual Approval & Simulator Verification
    safety = ResponseSafetyValidator()
    action = safety.validate_and_simulate_action(
        incident_id=candidate.candidate_id,
        tenant_id=profile.tenant_id,
        action_type="TEMPORARY_BLOCK",
        target=candidate.advisory_recommendation["target"],
        duration_seconds=candidate.advisory_recommendation["duration_seconds"],
        approver_id="responder_alpha",
        approver_role="SECURITY_RESPONDER",
        idempotency_key="idemp-e2e-lifecycle",
    )
    assert action.status == "SIMULATED_ACTIVE"
    assert action.state_verified is True
    assert action.target in safety.get_active_simulated_rules()

    # 6. Expiry and simulated rollback
    assert safety.simulate_rollback(action.target) is True
    assert action.target not in safety.get_active_simulated_rules()

    # 7. Seven-Day Shadow Evaluation Scenario Replay
    eval_7d = SevenDayEvaluator(profile.pilot_id, profile.tenant_id, is_simulation=True)
    report_7d = eval_7d.run_simulated_7_day_scenario()
    assert report_7d.days_completed == 7
    assert report_7d.target_met_le_5_false_per_day is True
    assert report_7d.analyst_capacity_target_met is True

    # 8. Complete Readiness Gate Audit (R01-R23)
    readiness = PilotReadinessEvaluator.evaluate_pilot_readiness(active_prof)
    assert readiness.final_readiness_decision == "READY_FOR_AUTHORIZED_SHADOW_PILOT"
    assert readiness.total_gates_evaluated == 23
    assert readiness.passed_count == 23
    assert readiness.auto_response_enabled is False
    assert readiness.zero_cost_verified is True
