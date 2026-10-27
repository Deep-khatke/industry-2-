"""Unit tests for Conventional ECDSA P-256 (SHA-384) signing."""

from fcs_governance.crypto.conventional import ConventionalSigner


def test_ecdsa_p256_sign_and_verify():
    """Verify standard ECDSA keypair generation, signing, and verification."""
    priv, pub = ConventionalSigner.generate_keypair()
    message = b"FCS Canonical Manifest Payload Test Bytes"

    sig_hex = ConventionalSigner.sign(priv, message)
    assert len(sig_hex) > 64

    # Valid verification
    assert ConventionalSigner.verify(pub, message, sig_hex) is True

    # Tampered message
    tampered_msg = b"FCS Tampered Payload Test Bytes"
    assert ConventionalSigner.verify(pub, tampered_msg, sig_hex) is False

    # Wrong public key
    _, wrong_pub = ConventionalSigner.generate_keypair()
    assert ConventionalSigner.verify(wrong_pub, message, sig_hex) is False


def test_ecdsa_key_serialization():
    """Verify DER hex public key round-trip serialization."""
    _, pub = ConventionalSigner.generate_keypair()
    hex_str = ConventionalSigner.public_key_to_hex(pub)
    loaded_pub = ConventionalSigner.public_key_from_hex(hex_str)

    msg = b"test message"
    priv, _ = ConventionalSigner.generate_keypair()
    sig = ConventionalSigner.sign(priv, msg)
    # Ensure loaded key behaves as original
    assert ConventionalSigner.verify(loaded_pub, msg, sig) == ConventionalSigner.verify(pub, msg, sig)


def test_ecdsa_key_id_derivation():
    """Verify deterministic Key ID generation."""
    _, pub = ConventionalSigner.generate_keypair()
    key_id = ConventionalSigner.get_key_id(pub)
    assert key_id.startswith("ecdsa-p256-")
    assert len(key_id) == len("ecdsa-p256-") + 16
