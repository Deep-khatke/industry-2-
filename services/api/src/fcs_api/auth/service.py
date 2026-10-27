"""Authentication service: password hashing, verification, and JWT issuance."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from ..config import settings


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


def create_access_token(
    user_id: str,
    username: str,
    tenant_id: str | None,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.jwt_expiration_minutes))
    payload: dict[str, Any] = {
        "sub": user_id,
        "username": username,
        "tenant_id": tenant_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
