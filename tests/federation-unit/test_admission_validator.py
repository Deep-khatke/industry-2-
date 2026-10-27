"""Unit tests for ParticipantAdmissionValidator governance and security checks."""

import pytest

from fcs_pfl.admission.validator import LOCKED_FEATURE_SCHEMA_DIGEST, ParticipantAdmissionValidator
from fcs_pfl.contracts.manifests import RoundManifest


@pytest.fixture
def valid_manifest() -> RoundManifest:
    return RoundManifest(
        round_id="round_valid_01",
        sequence=1,
        cohort=["isp_01", "isp_02"],
        base_model_digest="0" * 64,
        feature_schema_digest=LOCKED_FEATURE_SCHEMA_DIGEST,
        coordinator_signature="fcs_dev_coordinator_signed",
        nonce="fresh_nonce_1",
    )


def test_admission_success(valid_manifest: RoundManifest) -> None:
    validator = ParticipantAdmissionValidator(tenant_id="isp_01")
    is_valid, reason = validator.validate(valid_manifest)
    assert is_valid
    assert reason is None


def test_admission_rejects_unauthorized_coordinator(valid_manifest: RoundManifest) -> None:
    valid_manifest.coordinator_signature = "rogue_coordinator"
    validator = ParticipantAdmissionValidator(tenant_id="isp_01")
    is_valid, reason = validator.validate(valid_manifest)
    assert not is_valid
    assert "UNAUTHORIZED_COORDINATOR" in reason


def test_admission_rejects_not_in_cohort(valid_manifest: RoundManifest) -> None:
    valid_manifest.cohort = ["isp_02", "isp_03"]
    validator = ParticipantAdmissionValidator(tenant_id="isp_01")
    is_valid, reason = validator.validate(valid_manifest)
    assert not is_valid
    assert "NOT_IN_COHORT" in reason


def test_admission_rejects_schema_mismatch(valid_manifest: RoundManifest) -> None:
    valid_manifest.feature_schema_digest = "corrupted_schema_digest"
    validator = ParticipantAdmissionValidator(tenant_id="isp_01")
    is_valid, reason = validator.validate(valid_manifest)
    assert not is_valid
    assert "SCHEMA_MISMATCH" in reason


def test_admission_rejects_replay_nonce(valid_manifest: RoundManifest) -> None:
    validator = ParticipantAdmissionValidator(tenant_id="isp_01")
    is_valid, _ = validator.validate(valid_manifest)
    assert is_valid

    # Replay same manifest
    is_valid2, reason2 = validator.validate(valid_manifest)
    assert not is_valid2
    assert "REPLAY_ATTACK_DETECTED" in reason2
