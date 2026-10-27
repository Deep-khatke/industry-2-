"""Unit tests for TrustStore and cryptographic key lifecycle."""

import pytest
from fcs_governance.contracts.manifest import SignatureAlgorithm
from fcs_governance.crypto.trust_store import KeyStatus, TrustStore


def test_trust_store_registration_and_trust_verification():
    """Verify key registration and trust validation."""
    ts = TrustStore()
    entry = ts.register_key(
        key_id="ecdsa-key-1",
        algorithm=SignatureAlgorithm.ECDSA_P256_SHA384,
        public_key_hex="aabbccdd11223344",
        owner_org="ISP_GOVERNANCE_A",
        valid_until="2099-01-01T00:00:00Z",
    )
    assert entry.status == KeyStatus.ACTIVE
    assert ts.is_key_trusted("ecdsa-key-1", "aabbccdd11223344") is True
    # Wrong public key
    assert ts.is_key_trusted("ecdsa-key-1", "wrongkeyhex") is False
    # Unknown key ID
    assert ts.is_key_trusted("non-existent-key", "aabbccdd11223344") is False


def test_trust_store_key_revocation():
    """Verify that revoked keys immediately fail trust validation."""
    ts = TrustStore()
    ts.register_key(
        key_id="mldsa-key-1",
        algorithm=SignatureAlgorithm.ML_DSA_65,
        public_key_hex="11223344",
        owner_org="PLATFORM_GOVERNANCE",
        valid_until="2099-01-01T00:00:00Z",
    )
    assert ts.is_key_trusted("mldsa-key-1", "11223344") is True

    # Revoke key
    ts.revoke_key("mldsa-key-1", "Key suspected of compromise")
    assert ts.is_key_trusted("mldsa-key-1", "11223344") is False
    assert ts.get_key("mldsa-key-1").status == KeyStatus.REVOKED


def test_trust_store_key_rotation():
    """Verify key rotation marks old key ROTATED and activates new key."""
    ts = TrustStore()
    ts.register_key(
        key_id="old-key",
        algorithm=SignatureAlgorithm.ECDSA_P256_SHA384,
        public_key_hex="oldhex",
        owner_org="ISP_GOVERNANCE_B",
        valid_until="2099-01-01T00:00:00Z",
    )

    ts.rotate_key(
        old_key_id="old-key",
        new_key_id="new-key",
        new_public_key_hex="newhex",
        valid_until="2099-01-01T00:00:00Z",
    )

    assert ts.is_key_trusted("old-key", "oldhex") is False
    assert ts.get_key("old-key").status == KeyStatus.ROTATED
    assert ts.is_key_trusted("new-key", "newhex") is True
