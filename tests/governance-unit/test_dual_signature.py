"""Unit tests for Dual-Signature (ECDSA + ML-DSA-65) manifest verification."""

import pytest
from fcs_governance.contracts.manifest import CanonicalManifestBody
from fcs_governance.crypto.dual_signer import DualSignatureVerificationError, DualSigner


@pytest.fixture
def sample_manifest_body():
    return CanonicalManifestBody(
        release_id="rel-dual-test-01",
        schema_version="1.2.0",
        manifest_sequence=1,
        artifact_digest_sha384="e" * 96,
        feature_schema_digest="f" * 64,
        model_lineage_reference="parent-candidate-01",
        evaluation_reference="eval-report-hash-123",
        validity_interval_start="2020-01-01T00:00:00Z",
        validity_interval_end="2099-01-01T00:00:00Z",
    )


def test_dual_signing_and_verification_success(sample_manifest_body):
    """Verify that both ECDSA and ML-DSA-65 signatures validate over identical canonical bytes."""
    signer, keys = DualSigner.create_ephemeral_dev_signer()
    manifest = signer.sign_manifest(sample_manifest_body)

    assert DualSigner.verify_manifest(
        manifest,
        expected_artifact_digest="e" * 96,
        trusted_ecdsa_key_hex=keys["ecdsa_public_key_hex"],
        trusted_mldsa_key_hex=keys["mldsa_public_key_hex"],
    ) is True


def test_dual_signature_tampered_artifact_digest(sample_manifest_body):
    """Verify failure when artifact digest does not match."""
    signer, _ = DualSigner.create_ephemeral_dev_signer()
    manifest = signer.sign_manifest(sample_manifest_body)

    with pytest.raises(DualSignatureVerificationError, match="Artifact digest mismatch"):
        DualSigner.verify_manifest(manifest, expected_artifact_digest="f" * 96)


def test_dual_signature_corrupted_ecdsa(sample_manifest_body):
    """Verify failure when ECDSA signature is corrupted."""
    signer, _ = DualSigner.create_ephemeral_dev_signer()
    manifest = signer.sign_manifest(sample_manifest_body)

    # Corrupt ECDSA signature
    manifest.conventional_signature.signature_hex = "00" * 32
    with pytest.raises(DualSignatureVerificationError, match="ECDSA signature verification failed"):
        DualSigner.verify_manifest(manifest)


def test_dual_signature_corrupted_mldsa(sample_manifest_body):
    """Verify failure when ML-DSA signature is corrupted."""
    signer, _ = DualSigner.create_ephemeral_dev_signer()
    manifest = signer.sign_manifest(sample_manifest_body)

    # Corrupt ML-DSA signature
    manifest.post_quantum_signature.signature_hex = "00" * 3293
    with pytest.raises(DualSignatureVerificationError, match="ML-DSA-65 signature verification failed"):
        DualSigner.verify_manifest(manifest)


def test_expired_manifest_rejection(sample_manifest_body):
    """Verify rejection of expired release manifest."""
    signer, _ = DualSigner.create_ephemeral_dev_signer()
    # Set validity in past
    sample_manifest_body.validity_interval_start = "2020-01-01T00:00:00Z"
    sample_manifest_body.validity_interval_end = "2020-01-02T00:00:00Z"

    manifest = signer.sign_manifest(sample_manifest_body)
    with pytest.raises(DualSignatureVerificationError, match="Manifest has expired"):
        DualSigner.verify_manifest(manifest, check_validity_window=True)
