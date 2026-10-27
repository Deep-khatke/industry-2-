"""Integration tests for FastAPI REST API endpoints."""

from fastapi.testclient import TestClient
from fcs_api.app import app
from fcs_api.database import reset_db, seed_demo_data

client = TestClient(app)


def setup_function():
    reset_db()
    seed_demo_data()


def test_auth_token_and_me():
    # Login as responder_alpha
    resp = client.post(
        "/v1/auth/token",
        json={"username": "responder_alpha", "password": "FcsDemo2026!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    token = data["access_token"]

    # Call /v1/auth/me
    me_resp = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me = me_resp.json()
    assert me["username"] == "responder_alpha"
    assert me["role"] == "SECURITY_RESPONDER"
    assert me["tenant_id"] == "rural-isp-alpha"


def test_overview_and_response_policy():
    # Login
    auth = client.post("/v1/auth/token", json={"username": "responder_alpha", "password": "FcsDemo2026!"}).json()
    token = auth["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # /v1/overview
    ov_resp = client.get("/v1/overview?tenant_id=rural-isp-alpha", headers=headers)
    assert ov_resp.status_code == 200
    ov = ov_resp.json()
    assert ov["tenant_id"] == "rural-isp-alpha"
    assert "flow_metrics" in ov
    assert "incident_metrics" in ov

    # /v1/response-policy
    pol_resp = client.get("/v1/response-policy", headers=headers)
    assert pol_resp.status_code == 200
    pol = pol_resp.json()
    assert pol["response_mode"] == "MANUAL"
    assert pol["auto_response_enabled"] is False
    assert "safety qualification phase" in pol["auto_response_status"]


def test_dev_replay_and_incident_flow():
    auth = client.post("/v1/auth/token", json={"username": "responder_alpha", "password": "FcsDemo2026!"}).json()
    token = auth["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Trigger suspicious replay
    replay_resp = client.post(
        "/v1/dev/replay/start",
        json={"scenario": "suspicious", "tenant_id": "rural-isp-alpha"},
        headers=headers,
    )
    assert replay_resp.status_code == 200
    replay_data = replay_resp.json()
    assert replay_data["replayed_flows"] == 40

    # List incidents
    inc_resp = client.get("/v1/incidents?tenant_id=rural-isp-alpha", headers=headers)
    assert inc_resp.status_code == 200
    inc_data = inc_resp.json()
    assert inc_data["total"] >= 1
    incident = inc_data["incidents"][0]
    inc_id = incident["incident_id"]

    # Approve manual action
    act_resp = client.post(
        f"/v1/incidents/{inc_id}/actions",
        json={
            "action_type": "TEMPORARY_BLOCK",
            "target": "203.0.113.88",
            "duration_seconds": 600,
            "idempotency_key": "api_test_idem_001",
            "scope": "EDGE_FIREWALL",
        },
        headers=headers,
    )
    assert act_resp.status_code == 200
    act_data = act_resp.json()
    assert act_data["status"] == "VERIFIED"
    action_id = act_data["action_id"]

    # Rollback action
    rb_resp = client.post(f"/v1/actions/{action_id}/rollback", headers=headers)
    assert rb_resp.status_code == 200
    assert rb_resp.json()["status"] == "ROLLED_BACK"
