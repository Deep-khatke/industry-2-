"""Controlled Adversarial Security Validation Suite for Phase 8.

Verifies boundary isolation, malformed telemetry rejection, IDOR prevention,
role escalation controls, ML artifact tamper detection, and AUTO response prevention.
"""

import pytest
import uuid
from packages.contracts.flow_event import FlowEvent
from services.telemetry_collector.protocol import IPFIXParser, ProtocolError
from fcs_api.database import seed_demo_data, get_db
from fcs_api.response.policy import ResponsePolicyEngine, ResponsePolicyError
from fcs_governance.crypto.dual_signer import DualSigner


@pytest.fixture(autouse=True)
def setup_db():
    seed_demo_data()


def test_malformed_telemetry_rejection():
    """Verify IPFIX parser rejects truncated byte frames and invalid lengths safely."""
    parser = IPFIXParser()
    truncated_bytes = b"\x00\x0a\x00\x10\x00\x00\x00\x01"  # Header claiming length 16, but only 8 bytes
    with pytest.raises((ProtocolError, ValueError)):
        parser.parse_header(truncated_bytes)


def test_cross_tenant_idor_incident_access():
    """Verify Tenant Bravo responder cannot approve or modify Tenant Alpha incident."""
    with get_db() as conn:
        alpha_inc = conn.execute("SELECT incident_id FROM incidents WHERE tenant_id = 'rural-isp-alpha' LIMIT 1").fetchone()
    
    if not alpha_inc:
        pytest.skip("No alpha incident found to test")

    incident_id = alpha_inc["incident_id"]
    bravo_user = {
        "user_id": "usr_bravo",
        "tenant_id": "rural-isp-bravo",
        "role": "SECURITY_RESPONDER",
    }

    with pytest.raises(ResponsePolicyError, match="Cross-tenant action rejected"):
        ResponsePolicyEngine.execute_manual_action(
            incident_id=incident_id,
            action_type="TEMPORARY_BLOCK",
            target="198.51.100.12",
            duration_seconds=60,
            acting_user=bravo_user,
            idempotency_key=f"sec_idem_{uuid.uuid4().hex[:8]}",
        )


def test_unauthorized_role_escalation():
    """Verify READ_ONLY auditor cannot execute manual response actions."""
    with get_db() as conn:
        alpha_inc = conn.execute("SELECT incident_id FROM incidents WHERE tenant_id = 'rural-isp-alpha' LIMIT 1").fetchone()

    if not alpha_inc:
        pytest.skip("No alpha incident found to test")

    incident_id = alpha_inc["incident_id"]
    viewer_user = {
        "user_id": "usr_viewer_alpha",
        "tenant_id": "rural-isp-alpha",
        "role": "READ_ONLY",
    }

    with pytest.raises(ResponsePolicyError, match="cannot approve defensive actions"):
        ResponsePolicyEngine.execute_manual_action(
            incident_id=incident_id,
            action_type="TEMPORARY_BLOCK",
            target="198.51.100.12",
            duration_seconds=60,
            acting_user=viewer_user,
            idempotency_key=f"sec_idem_{uuid.uuid4().hex[:8]}",
        )


def test_automatic_response_mode_prohibition():
    """Verify that attempting to toggle or execute AUTO response is strictly prohibited."""
    with get_db() as conn:
        alpha_inc = conn.execute("SELECT incident_id FROM incidents WHERE tenant_id = 'rural-isp-alpha' LIMIT 1").fetchone()

    if not alpha_inc:
        pytest.skip("No alpha incident found to test")

    incident_id = alpha_inc["incident_id"]
    acting_user = {
        "user_id": "usr_admin_alpha",
        "tenant_id": "rural-isp-alpha",
        "role": "TENANT_ADMIN",
    }

    # Verify that action types cannot include AUTO_EXECUTE
    with pytest.raises(ResponsePolicyError, match="Invalid action type"):
        ResponsePolicyEngine.execute_manual_action(
            incident_id=incident_id,
            action_type="AUTO_FIREWALL_EXECUTE",
            target="198.51.100.12",
            duration_seconds=60,
            acting_user=acting_user,
            idempotency_key=f"sec_idem_{uuid.uuid4().hex[:8]}",
        )


def test_tampered_model_manifest_dual_signature():
    """Verify dual signature verification rejects tampered payload bytes."""
    from fcs_governance.contracts.manifest import CanonicalManifestBody
    from fcs_governance.crypto.dual_signer import DualSignatureVerificationError
    from datetime import datetime, timezone, timedelta

    signer, pks = DualSigner.create_ephemeral_dev_signer()
    now_dt = datetime.now(timezone.utc)
    body = CanonicalManifestBody(
        release_id=str(uuid.uuid4()),
        manifest_sequence=1,
        artifact_digest_sha384="a" * 96,
        feature_schema_digest="b" * 64,
        model_lineage_reference="parent_cand_01",
        evaluation_reference="eval_rep_01",
        validity_interval_start=(now_dt - timedelta(hours=1)).isoformat(),
        validity_interval_end=(now_dt + timedelta(hours=24)).isoformat(),
    )
    envelope = signer.sign_manifest(body)

    # Verify untampered
    assert DualSigner.verify_manifest(envelope) is True

    # Tamper payload
    envelope.body.artifact_digest_sha384 = "c" * 96
    with pytest.raises(DualSignatureVerificationError):
        DualSigner.verify_manifest(envelope)

