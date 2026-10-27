"""Unit tests for Post-Quantum ML-DSA-65 (NIST FIPS 204 / Dilithium3) signing."""

from fcs_governance.crypto.post_quantum import PostQuantumSigner


def test_mldsa_65_sign_and_verify():
    """Verify ML-DSA-65 keypair generation, direct message signing, and verification."""
    pk, sk = PostQuantumSigner.generate_keypair()
    assert len(pk) == 1952
    assert len(sk) == 4000

    message = b"FCS Canonical Manifest Payload for Post-Quantum ML-DSA-65"
    sig_hex = PostQuantumSigner.sign(sk, message)
    assert len(sig_hex) == 3293 * 2  # 6586 hex characters

    # Valid verification
    assert PostQuantumSigner.verify(pk, message, sig_hex) is True

    # Tampered message rejection
    tampered = b"FCS Tampered Manifest Payload"
    assert PostQuantumSigner.verify(pk, tampered, sig_hex) is False

    # Wrong public key rejection
    wrong_pk, _ = PostQuantumSigner.generate_keypair()
    assert PostQuantumSigner.verify(wrong_pk, message, sig_hex) is False


def test_mldsa_65_key_serialization():
    """Verify hex encoding and decoding of ML-DSA-65 public and secret keys."""
    pk, sk = PostQuantumSigner.generate_keypair()
    pk_hex = PostQuantumSigner.public_key_to_hex(pk)
    sk_hex = PostQuantumSigner.secret_key_to_hex(sk)

    loaded_pk = PostQuantumSigner.public_key_from_hex(pk_hex)
    loaded_sk = PostQuantumSigner.secret_key_from_hex(sk_hex)

    assert loaded_pk == pk
    assert loaded_sk == sk


def test_mldsa_65_key_id_derivation():
    """Verify deterministic Key ID generation for ML-DSA-65."""
    pk, _ = PostQuantumSigner.generate_keypair()
    key_id = PostQuantumSigner.get_key_id(pk)
    assert key_id.startswith("mldsa-65-")
    assert len(key_id) == len("mldsa-65-") + 16
