"""Cryptographic hashing and verification utilities."""

import hashlib
import hmac


def hash_bytes(data: bytes, algorithm: str = "sha256") -> str:
    """Compute cryptographic hash of raw bytes."""
    h = hashlib.new(algorithm)
    h.update(data)
    return h.hexdigest()


def compute_hmac(key: bytes, message: bytes, algorithm: str = "sha256") -> str:
    """Compute keyed HMAC."""
    return hmac.new(key, message, getattr(hashlib, algorithm)).hexdigest()


def verify_hash(data: bytes, expected_hash: str, algorithm: str = "sha256") -> bool:
    """Constant-time verification of cryptographic hash."""
    computed = hash_bytes(data, algorithm)
    return hmac.compare_digest(computed, expected_hash)
