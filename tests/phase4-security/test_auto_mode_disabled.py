"""Security test verifying that AUTO Response Mode is strictly disabled in Phase 4."""

from fastapi.testclient import TestClient
from fcs_api.app import app
from fcs_api.config import settings

client = TestClient(app)


def test_auto_response_mode_is_strictly_disabled():
    # 1. Config invariant check
    assert settings.response_mode == "MANUAL", "Phase 4 must strictly enforce MANUAL response mode"

    # 2. Login to obtain token
    auth = client.post(
        "/v1/auth/token",
        json={"username": "responder_alpha", "password": "FcsDemo2026!"},
    ).json()
    token = auth["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. API response policy check
    resp = client.get("/v1/response-policy", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["response_mode"] == "MANUAL"
    assert data["auto_response_enabled"] is False
    assert "AUTO response is unavailable until the dedicated safety qualification phase." in data["auto_response_status"]
