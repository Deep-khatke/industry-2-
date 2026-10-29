"""Phase 11: Authentication & Authorization Security Hardening Tests."""

from datetime import timedelta
from fastapi.testclient import TestClient
import pytest

from fcs_api.app import app
from fcs_api.auth.service import (
    create_access_token,
    decode_access_token,
    is_token_revoked,
    reset_failed_attempts,
    revoke_token,
)
from fcs_api.config import settings

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_auth_state():
    reset_failed_attempts("test_brute_user")
    reset_failed_attempts("responder_alpha")
    yield
    reset_failed_attempts("test_brute_user")
    reset_failed_attempts("responder_alpha")


def test_auth_login_successful_and_me():
    """Verify standard valid login generates verified JWT token with issuer and audience."""
    resp = client.post(
        "/v1/auth/token",
        json={"username": "responder_alpha", "password": "FcsDemo2026!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    token = data["access_token"]

    payload = decode_access_token(token)
    assert payload["iss"] == "federated-cyber-shield"
    assert payload["aud"] == "fcs-api"
    assert payload["username"] == "responder_alpha"
    assert payload["tenant_id"] == "rural-isp-alpha"


def test_auth_brute_force_lockout():
    """Verify after 5 consecutive incorrect passwords, client receives HTTP 429 Too Many Requests."""
    for i in range(5):
        resp = client.post(
            "/v1/auth/token",
            json={"username": "test_brute_user", "password": f"WrongPass{i}!"},
        )
        assert resp.status_code == 401

    # 6th attempt should be blocked with 429
    locked_resp = client.post(
        "/v1/auth/token",
        json={"username": "test_brute_user", "password": "AnyPassword!"},
    )
    assert locked_resp.status_code == 429
    assert "Too many failed authentication attempts" in locked_resp.json()["detail"]


def test_auth_token_revocation_and_logout():
    """Verify logout invalidates token and revoked token cannot access protected routes."""
    login_resp = client.post(
        "/v1/auth/token",
        json={"username": "responder_alpha", "password": "FcsDemo2026!"},
    )
    token = login_resp.json()["access_token"]

    # Access /v1/auth/me successfully
    me_resp = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200

    # Logout
    logout_resp = client.post("/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_resp.status_code == 200
    assert logout_resp.json()["status"] == "SUCCESS"
    assert is_token_revoked(token) is True

    # Subsequent access with same token must fail with 401
    me_after_resp = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_after_resp.status_code == 401
    assert "revoked" in me_after_resp.json()["detail"].lower()


def test_auth_expired_token_rejected():
    """Verify expired token is rejected with 401 Unauthorized."""
    expired_token = create_access_token(
        user_id="user_responder_alpha",
        username="responder_alpha",
        tenant_id="rural-isp-alpha",
        role="SECURITY_RESPONDER",
        expires_delta=timedelta(seconds=-10),  # expired 10 seconds ago
    )

    resp = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


def test_demo_accounts_rejected_outside_development(monkeypatch):
    """Verify demo credentials cannot authenticate when allow_demo_credentials is False."""
    monkeypatch.setattr(settings, "allow_demo_credentials", False)

    resp = client.post(
        "/v1/auth/token",
        json={"username": "responder_alpha", "password": "FcsDemo2026!"},
    )
    assert resp.status_code == 403
    assert "strictly prohibited" in resp.json()["detail"].lower()
