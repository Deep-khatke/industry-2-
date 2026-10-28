"""Unit tests for Phase 9 ISP Onboarding, Exporter Compatibility, and Retention."""

import pytest
from datetime import UTC, datetime, timedelta

from fcs_pilot.onboarding.models import EnvironmentMode, NetworkScope, OnboardingStatus, PilotProfile
from fcs_pilot.onboarding.state_machine import OnboardingError, OnboardingStateMachine
from fcs_pilot.exporter_compatibility.registry import ExporterCapabilityRegistry
from fcs_pilot.exporter_compatibility.checker import ExporterCompatibilityChecker
from fcs_pilot.exporter_compatibility.feature_parity import FeatureParityValidator
from fcs_pilot.retention.retention_manager import DataRetentionManager
from fcs_pilot.metrics.false_alert_meter import FalseAlertMeter
from fcs_pilot.analyst_feedback.feedback_manager import AnalystFeedbackManager, IncidentDisposition


def test_onboarding_state_machine_valid_progression():
    """Verify standard valid transition progression from DRAFT to SHADOW_ACTIVE."""
    profile = PilotProfile(
        pilot_id="pilot-test-01",
        tenant_id="rural-isp-alpha",
        isp_display_name="Test ISP",
        environment_mode=EnvironmentMode.MODE_A_SYNTHETIC,
        status=OnboardingStatus.DRAFT,
        technical_contact="soc@test.example",
    )
    sm = OnboardingStateMachine([profile])

    # 1. DRAFT -> AUTHORIZATION_PENDING
    p1 = sm.transition_state("pilot-test-01", OnboardingStatus.AUTHORIZATION_PENDING, "admin1", "PLATFORM_ADMIN", "Initiated")
    assert p1.status == OnboardingStatus.AUTHORIZATION_PENDING

    # 2. AUTHORIZATION_PENDING -> TECHNICAL_REVIEW
    p2 = sm.transition_state("pilot-test-01", OnboardingStatus.TECHNICAL_REVIEW, "admin1", "PLATFORM_ADMIN", "Legal verified")
    assert p2.status == OnboardingStatus.TECHNICAL_REVIEW

    # 3. TECHNICAL_REVIEW -> SECURITY_REVIEW
    p3 = sm.transition_state("pilot-test-01", OnboardingStatus.SECURITY_REVIEW, "admin1", "PLATFORM_ADMIN", "Exporter checked")
    assert p3.status == OnboardingStatus.SECURITY_REVIEW

    # 4. SECURITY_REVIEW -> READY_FOR_SHADOW
    p4 = sm.transition_state("pilot-test-01", OnboardingStatus.READY_FOR_SHADOW, "admin1", "PLATFORM_ADMIN", "Security passed")
    assert p4.status == OnboardingStatus.READY_FOR_SHADOW

    # 5. READY_FOR_SHADOW -> SHADOW_ACTIVE
    p5 = sm.transition_state("pilot-test-01", OnboardingStatus.SHADOW_ACTIVE, "admin1", "PLATFORM_ADMIN", "Activated")
    assert p5.status == OnboardingStatus.SHADOW_ACTIVE

    # Verify audit trail length
    trail = sm.get_audit_trail("pilot-test-01")
    assert len(trail) == 5


def test_onboarding_unauthorized_role_rejected():
    """Verify non-admin roles cannot transition pilot onboarding states."""
    profile = PilotProfile(
        pilot_id="pilot-test-02",
        tenant_id="rural-isp-alpha",
        isp_display_name="Test ISP",
        environment_mode=EnvironmentMode.MODE_A_SYNTHETIC,
        status=OnboardingStatus.DRAFT,
        technical_contact="soc@test.example",
    )
    sm = OnboardingStateMachine([profile])

    with pytest.raises(OnboardingError, match="Unauthorized: Role 'SECURITY_ANALYST' cannot change pilot states"):
        sm.transition_state("pilot-test-02", OnboardingStatus.AUTHORIZATION_PENDING, "analyst1", "SECURITY_ANALYST", "Illegal transition")


def test_onboarding_illegal_state_skip():
    """Verify state machine rejects jumping directly from DRAFT to SHADOW_ACTIVE."""
    profile = PilotProfile(
        pilot_id="pilot-test-03",
        tenant_id="rural-isp-alpha",
        isp_display_name="Test ISP",
        environment_mode=EnvironmentMode.MODE_A_SYNTHETIC,
        status=OnboardingStatus.DRAFT,
        technical_contact="soc@test.example",
    )
    sm = OnboardingStateMachine([profile])

    with pytest.raises(OnboardingError, match="Illegal transition"):
        sm.transition_state("pilot-test-03", OnboardingStatus.SHADOW_ACTIVE, "admin1", "PLATFORM_ADMIN", "Illegal jump")


def test_exporter_capability_registry():
    """Verify registry contains Cisco, Juniper, MikroTik, Linux profiles."""
    profiles = ExporterCapabilityRegistry.list_all()
    assert "cisco_asr" in profiles
    assert "juniper_mx" in profiles
    assert "mikrotik_ccr" in profiles
    assert "linux_softflowd" in profiles

    cisco = ExporterCapabilityRegistry.get_profile("cisco_asr")
    assert cisco is not None
    assert cisco.vendor == "Cisco"
    assert "IPFIX" in cisco.supported_protocols
    assert len(cisco.supported_fields) >= 10


def test_exporter_compatibility_checker():
    """Verify checker validates template fields, sequences, and clock drift."""
    checker = ExporterCompatibilityChecker()
    valid_batch = [{
        "sourceIPv4Address": "10.0.1.5",
        "destinationIPv4Address": "192.168.1.10",
        "sourceTransportPort": 443,
        "destinationTransportPort": 51234,
        "protocolIdentifier": 6,
        "octetDeltaCount": 1500,
        "packetDeltaCount": 10,
        "flowStartMilliseconds": int(datetime.now(UTC).timestamp() * 1000) - 5000,
        "flowEndMilliseconds": int(datetime.now(UTC).timestamp() * 1000),
    }]

    res = checker.check_record_batch("exp-01", "Cisco", "IPFIX", valid_batch, sequence_number=10)
    assert res.template_valid is True
    assert res.status == "COMPATIBLE"
    assert len(res.missing_required_fields) == 0

    # Sequence gap test
    res_gap = checker.check_record_batch("exp-01", "Cisco", "IPFIX", valid_batch, sequence_number=15)
    assert res_gap.sequence_gap_detected is True
    assert res_gap.sequence_gap_count == 4


def test_feature_parity_validator():
    """Verify feature parity check matches deployable features and identifies missing fields."""
    val = FeatureParityValidator()
    res = val.evaluate_parity("exp-01", "Cisco", "IPFIX", [
        "sourceIPv4Address", "destinationIPv4Address", "sourceTransportPort",
        "destinationTransportPort", "protocolIdentifier", "octetDeltaCount",
        "packetDeltaCount", "tcpControlBits", "flowStartMilliseconds", "flowEndMilliseconds",
    ])
    assert res.parity_percentage > 50.0
    assert "syn_flood_specialist" in res.compatible_models
    assert "general_anomaly_model" in res.compatible_models


def test_retention_manager_purging():
    """Verify automated age-based purging while protecting active investigation IDs."""
    ret_mgr = DataRetentionManager("rural-isp-alpha", {"raw_telemetry_flows": 7})
    now = datetime.now(UTC)

    old_dt = now - timedelta(days=10)
    recent_dt = now - timedelta(days=2)

    items = [
        {"id": "flow-old-1", "timestamp": old_dt.isoformat()},
        {"id": "flow-old-protected", "timestamp": old_dt.isoformat()},
        {"id": "flow-recent-1", "timestamp": recent_dt.isoformat()},
    ]

    retained, audit = ret_mgr.evaluate_and_purge_expired(
        category="raw_telemetry_flows",
        items=items,
        protected_ids={"flow-old-protected"},
    )

    assert len(retained) == 2
    assert audit.items_purged == 1
    assert any(i["id"] == "flow-old-protected" for i in retained)
    assert any(i["id"] == "flow-recent-1" for i in retained)
