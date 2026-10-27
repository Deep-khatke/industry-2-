"""
Post-Quantum Cryptographic Signing using ML-DSA-65 (NIST FIPS 204 / Dilithium3).
Provides quantum-resilient digital signatures over canonical manifest bytes.
FCS Architecture v1.2 | Zero-Cost Invariant: ₹0 / $0
"""

from __future__ import annotations

import hashlib
from typing import Tuple
from dilithium_py.dilithium import Dilithium3


class PostQuantumSigner:
    """
    Manages ML-DSA-65 (NIST Level 3 / Dilithium3) key generation,
    direct message signing, and signature verification.
    """

    @staticmethod
    def generate_keypair() -> Tuple[bytes, bytes]:
        """
        Generate an ML-DSA-65 keypair.
        Returns:
            Tuple of (public_key_bytes, secret_key_bytes).
            Public key is 1952 bytes; secret key is 4000 bytes.
        """
        pk, sk = Dilithium3.keygen()
        return pk, sk

    @staticmethod
    def public_key_to_hex(public_key: bytes) -> str:
        """Hex-encode ML-DSA-65 public key."""
        return public_key.hex()

    @staticmethod
    def public_key_from_hex(hex_str: str) -> bytes:
        """Decode ML-DSA-65 public key from hex."""
        pk = bytes.fromhex(hex_str)
        if len(pk) != 1952:
            raise ValueError(
                f"Invalid ML-DSA-65 public key length: expected 1952 bytes, got {len(pk)}"
            )
        return pk

    @staticmethod
    def secret_key_to_hex(secret_key: bytes) -> str:
        """Hex-encode ML-DSA-65 secret key."""
        return secret_key.hex()

    @staticmethod
    def secret_key_from_hex(hex_str: str) -> bytes:
        """Decode ML-DSA-65 secret key from hex."""
        sk = bytes.fromhex(hex_str)
        if len(sk) != 4000:
            raise ValueError(
                f"Invalid ML-DSA-65 secret key length: expected 4000 bytes, got {len(sk)}"
            )
        return sk

    @staticmethod
    def sign(secret_key: bytes, message: bytes) -> str:
        """
        Sign canonical message bytes directly using ML-DSA-65 (direct-message signing).
        Returns hexadecimal signature string (3293 bytes -> 6586 hex chars).
        """
        if len(secret_key) != 4000:
            raise ValueError(f"Invalid ML-DSA-65 secret key length: {len(secret_key)}")
        signature_bytes = Dilithium3.sign(secret_key, message)
        return signature_bytes.hex()

    @staticmethod
    def verify(public_key: bytes, message: bytes, signature_hex: str) -> bool:
        """
        Verify an ML-DSA-65 signature over the canonical message bytes.
        Returns True if valid, False if invalid, corrupted, or signed by another key.
        """
        try:
            signature_bytes = bytes.fromhex(signature_hex)
            if len(public_key) != 1952:
                return False
            # Dilithium3.verify returns True or False
            return bool(Dilithium3.verify(public_key, message, signature_bytes))
        except Exception:
            return False

    @staticmethod
    def get_key_id(public_key: bytes) -> str:
        """Generate deterministic Key ID as truncated SHA-256 of ML-DSA-65 public key."""
        return f"mldsa-65-{hashlib.sha256(public_key).hexdigest()[:16]}"
