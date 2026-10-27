"""
Conventional Cryptographic Signing using ECDSA P-256 with SHA-384.
Complies with NIST SP 800-186 and FIPS 186-5.
FCS Architecture v1.2 | Zero-Cost Invariant: ₹0 / $0
"""

from __future__ import annotations

import hashlib
from typing import Tuple
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


class ConventionalSigner:
    """Manages ECDSA P-256 key generation, signing, and verification with SHA-384."""

    @staticmethod
    def generate_keypair() -> Tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
        """Generate a fresh ephemeral or development ECDSA P-256 keypair."""
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        return private_key, public_key

    @staticmethod
    def public_key_to_hex(public_key: ec.EllipticCurvePublicKey) -> str:
        """Serialize public key to uncompressed DER hex."""
        der_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return der_bytes.hex()

    @staticmethod
    def public_key_from_hex(hex_str: str) -> ec.EllipticCurvePublicKey:
        """Load public key from uncompressed DER hex."""
        der_bytes = bytes.fromhex(hex_str)
        public_key = serialization.load_der_public_key(der_bytes)
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            raise ValueError("Loaded key is not an EllipticCurvePublicKey")
        return public_key

    @staticmethod
    def private_key_to_pem(private_key: ec.EllipticCurvePrivateKey) -> str:
        """Serialize private key to PEM format."""
        pem_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return pem_bytes.decode("utf-8")

    @staticmethod
    def private_key_from_pem(pem_str: str) -> ec.EllipticCurvePrivateKey:
        """Load private key from PEM string."""
        private_key = serialization.load_pem_private_key(
            pem_str.encode("utf-8"),
            password=None,
        )
        if not isinstance(private_key, ec.EllipticCurvePrivateKey):
            raise ValueError("Loaded key is not an EllipticCurvePrivateKey")
        return private_key

    @staticmethod
    def sign(private_key: ec.EllipticCurvePrivateKey, message: bytes) -> str:
        """
        Sign message bytes using ECDSA with SHA-384.
        Returns hexadecimal DER-encoded signature.
        """
        signature = private_key.sign(
            message,
            ec.ECDSA(hashes.SHA384()),
        )
        return signature.hex()

    @staticmethod
    def verify(public_key: ec.EllipticCurvePublicKey, message: bytes, signature_hex: str) -> bool:
        """
        Verify an ECDSA signature over the message bytes using SHA-384.
        Returns True if valid, False if invalid or tampered.
        """
        try:
            signature_bytes = bytes.fromhex(signature_hex)
            public_key.verify(
                signature_bytes,
                message,
                ec.ECDSA(hashes.SHA384()),
            )
            return True
        except (InvalidSignature, ValueError):
            return False

    @staticmethod
    def get_key_id(public_key: ec.EllipticCurvePublicKey) -> str:
        """Generate deterministic Key ID as truncated SHA-256 of DER public key."""
        der_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return f"ecdsa-p256-{hashlib.sha256(der_bytes).hexdigest()[:16]}"
