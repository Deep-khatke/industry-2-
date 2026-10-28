"""Security and Tenant Isolation tests for Phase 9 Pilot."""

import pytest

from fcs_pilot.response_validation.safety_validator import (
    ProtectedInfrastructureViolation,
    ResponseSafetyValidator,
    UnauthorizedResponderError,
)


def test_reject_blocking_protected_infrastructure():
    """Verify actions targeting critical ISP infrastructure (DNS, gateways) are rejected."""
    safety = ResponseSafetyValidator()

    protected_ips = ["8.8.8.8", "1.1.1.1", "10.0.0.1", "192.168.1.1", "10.255.255.1"]
    for ip in protected_ips:
        with pytest.raises(ProtectedInfrastructureViolation, match="SAFETY VIOLATION"):
            safety.validate_and_simulate_action(
                incident_id="inc-sec-01",
                tenant_id="rural-isp-alpha",
                action_type="TEMPORARY_BLOCK",
                target=ip,
                duration_seconds=300,
                approver_id="responder1",
                approver_role="SECURITY_RESPONDER",
                idempotency_key=f"idemp-{ip}",
            )


def test_reject_unauthorized_responder_role():
    """Verify Tier-1 analysts cannot approve defensive actions without responder role."""
    safety = ResponseSafetyValidator()

    with pytest.raises(UnauthorizedResponderError, match="cannot approve defensive actions"):
        safety.validate_and_simulate_action(
            incident_id="inc-sec-02",
            tenant_id="rural-isp-alpha",
            action_type="TEMPORARY_BLOCK",
            target="198.51.100.77",
            duration_seconds=300,
            approver_id="analyst1",
            approver_role="SECURITY_ANALYST",
            idempotency_key="idemp-unauth",
        )


def test_duration_bounds_enforced():
    """Verify permanent blocks (<60s or >3600s) are rejected."""
    safety = ResponseSafetyValidator()

    # Too short (< 60s)
    with pytest.raises(ValueError, match="out of safe operational range"):
        safety.validate_and_simulate_action(
            incident_id="inc-sec-03",
            tenant_id="rural-isp-alpha",
            action_type="TEMPORARY_BLOCK",
            target="198.51.100.88",
            duration_seconds=10,
            approver_id="responder1",
            approver_role="SECURITY_RESPONDER",
            idempotency_key="idemp-short",
        )

    # Too long (> 3600s)
    with pytest.raises(ValueError, match="out of safe operational range"):
        safety.validate_and_simulate_action(
            incident_id="inc-sec-04",
            tenant_id="rural-isp-alpha",
            action_type="TEMPORARY_BLOCK",
            target="198.51.100.88",
            duration_seconds=86400,
            approver_id="responder1",
            approver_role="SECURITY_RESPONDER",
            idempotency_key="idemp-long",
        )


def test_idempotency_duplicate_execution_protection():
    """Verify using identical idempotency key returns cached record without re-executing."""
    safety = ResponseSafetyValidator()

    act1 = safety.validate_and_simulate_action(
        incident_id="inc-sec-05",
        tenant_id="rural-isp-alpha",
        action_type="TEMPORARY_BLOCK",
        target="198.51.100.99",
        duration_seconds=300,
        approver_id="responder1",
        approver_role="SECURITY_RESPONDER",
        idempotency_key="idemp-unique-123",
    )

    act2 = safety.validate_and_simulate_action(
        incident_id="inc-sec-05",
        tenant_id="rural-isp-alpha",
        action_type="TEMPORARY_BLOCK",
        target="198.51.100.99",
        duration_seconds=300,
        approver_id="responder1",
        approver_role="SECURITY_RESPONDER",
        idempotency_key="idemp-unique-123",
    )

    assert act1.action_id == act2.action_id
    assert len(safety.get_action_journal()) == 1
