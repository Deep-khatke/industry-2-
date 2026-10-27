"""Security tests verifying threat mitigation (cross-tenant isolation, tampering, replay)."""

import pytest

from fcs_pfl.admission.validator import LOCKED_FEATURE_SCHEMA_DIGEST, ParticipantAdmissionValidator
from fcs_pfl.client.loader import TenantPartitionLoader
from fcs_pfl.contracts.manifests import RoundManifest


def test_cross_tenant_isolation_boundary() -> None:
    loader = TenantPartitionLoader(participant_id="isp_01")
    # Attempt to load an unauthorized tenant's data directly
    with pytest.raises(PermissionError):
        loader.load_tensors(client_id="rogue_tenant_outside_cohort")


def test_unauthorized_coordinator_impersonation() -> None:
    manifest = RoundManifest(
        round_id="r_hack_01",
        cohort=["isp_01"],
        base_model_digest="0" * 64,
        coordinator_signature="untrusted_attacker_key",
        nonce="attack_nonce_1",
    )
    validator = ParticipantAdmissionValidator(tenant_id="isp_01")
    is_valid, reason = validator.validate(manifest)
    assert not is_valid
    assert "UNAUTHORIZED_COORDINATOR" in reason


def test_feature_schema_tampering_rejected() -> None:
    manifest = RoundManifest(
        round_id="r_tamper_01",
        cohort=["isp_01"],
        base_model_digest="0" * 64,
        feature_schema_digest="tampered_unapproved_14_feature_hash",
        coordinator_signature="fcs_dev_coordinator_signed",
        nonce="tamper_nonce_2",
    )
    validator = ParticipantAdmissionValidator(tenant_id="isp_01")
    is_valid, reason = validator.validate(manifest)
    assert not is_valid
    assert "SCHEMA_MISMATCH" in reason
