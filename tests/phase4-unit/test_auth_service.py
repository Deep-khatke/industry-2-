"""Unit tests for PBKDF2 password hashing and JWT token issuance."""

from datetime import timedelta

from fcs_api.auth.service import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing_and_verification():
    raw_password = "SecureSOCPassword2026!"
    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert hashed.startswith("pbkdf2_sha256$")

    # Correct password succeeds
    assert verify_password(raw_password, hashed) is True

    # Wrong password fails
    assert verify_password("WrongPassword123", hashed) is False


def test_jwt_token_creation_and_decoding():
    token = create_access_token(
        user_id="usr_test_01",
        username="analyst_bob",
        tenant_id="rural-isp-alpha",
        role="SECURITY_ANALYST",
        expires_delta=timedelta(minutes=60),
    )

    assert isinstance(token, str)
    payload = decode_access_token(token)

    assert payload["sub"] == "usr_test_01"
    assert payload["username"] == "analyst_bob"
    assert payload["tenant_id"] == "rural-isp-alpha"
    assert payload["role"] == "SECURITY_ANALYST"
