"""Authentication service: password hashing, verification, rate limiting, and JWT issuance."""

from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import secrets
import time
from typing import Any
import uuid

import jwt

from ..config import settings

# In-memory revocation set (Phase 11 development hardening)
_revoked_tokens: set[str] = set()

# In-memory authentication failure tracking: identifier -> list of timestamps
_failed_attempts: dict[str, list[float]] = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 60.0


def hash_password(password: str, salt: str | None = None) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 rounds."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000,
    )
    return f"pbkdf2_sha256$100000${salt}${key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify raw password against stored PBKDF2 hash."""
    try:
        parts = stored_hash.split("$")
        if len(parts) == 4 and parts[0] == "pbkdf2_sha256":
            rounds = int(parts[1])
            salt = parts[2]
            expected_hex = parts[3]
            key = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                rounds,
            )
            return hmac.compare_digest(key.hex(), expected_hex)
        elif len(parts) == 3:
            meta, salt, expected_hex = parts
            rounds = int(meta.split(":")[2])
            key = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                rounds,
            )
            return hmac.compare_digest(key.hex(), expected_hex)
        return False
    except Exception:
        return False


def record_failed_attempt(identifier: str) -> int:
    """Record a failed login attempt and return current count in window."""
    now = time.time()
    attempts = _failed_attempts.setdefault(identifier, [])
    # Filter attempts outside window
    attempts = [t for t in attempts if now - t < LOCKOUT_WINDOW_SECONDS]
    attempts.append(now)
    _failed_attempts[identifier] = attempts
    return len(attempts)


def is_rate_limited(identifier: str) -> bool:
    """Check if identifier has exceeded maximum failed attempts in window."""
    now = time.time()
    attempts = _failed_attempts.get(identifier, [])
    active = [t for t in attempts if now - t < LOCKOUT_WINDOW_SECONDS]
    _failed_attempts[identifier] = active
    return len(active) >= MAX_FAILED_ATTEMPTS


def reset_failed_attempts(identifier: str) -> None:
    """Reset failed attempts for identifier on successful authentication."""
    _failed_attempts.pop(identifier, None)


def revoke_token(token: str) -> None:
    """Revoke an active JWT token."""
    _revoked_tokens.add(token)


def is_token_revoked(token: str) -> bool:
    """Check if token has been explicitly revoked."""
    return token in _revoked_tokens


def create_access_token(
    user_id: str,
    username: str,
    tenant_id: str | None,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token with unique JTI, issuer, and audience claims."""
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.jwt_expiration_minutes))
    payload: dict[str, Any] = {
        "jti": str(uuid.uuid4()),
        "sub": user_id,
        "username": username,
        "tenant_id": tenant_id,
        "role": role,
        "iss": "federated-cyber-shield",
        "aud": "fcs-api",
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token, verifying expiration and revocation."""
    if is_token_revoked(token):
        raise ValueError("Token has been revoked.")

    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"verify_exp": True, "verify_signature": True, "verify_aud": False},
    )
