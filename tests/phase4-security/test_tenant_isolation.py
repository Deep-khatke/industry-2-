"""Security tests for multi-tenant ISP isolation (G01 Release Gate)."""

from fastapi.testclient import TestClient
from fcs_api.app import app
from fcs_api.database import reset_db, seed_demo_data
from fcs_api.telemetry.replay import ReplayCoordinator

client = TestClient(app)


def setup_function():
    reset_db()
    seed_demo_data()


def test_cross_tenant_idor_incident_access_denied():
    # 1. Generate an incident under rural-isp-bravo
    ReplayCoordinator.run_scenario("suspicious", tenant_id="rural-isp-bravo")

    # 2. Login as user of rural-isp-alpha
    auth_alpha = client.post(
        "/v1/auth/token",
        json={"username": "responder_alpha", "password": "FcsDemo2026!"},
    ).json()
    token_alpha = auth_alpha["access_token"]
    headers_alpha = {"Authorization": f"Bearer {token_alpha}"}

    # 3. Attempt to query incidents for rural-isp-bravo using alpha token -> Must return 403
    resp = client.get("/v1/incidents?tenant_id=rural-isp-bravo", headers=headers_alpha)
    assert resp.status_code == 403
    assert "Cross-tenant access" in resp.json()["detail"]


def test_cross_tenant_action_approval_denied():
    # 1. Generate an incident under rural-isp-bravo
    ReplayCoordinator.run_scenario("suspicious", tenant_id="rural-isp-bravo")

    # Get incident ID for bravo
    auth_bravo = client.post(
        "/v1/auth/token",
        json={"username": "responder_bravo", "password": "FcsDemo2026!"},
    ).json()
    token_bravo = auth_bravo["access_token"]
    headers_bravo = {"Authorization": f"Bearer {token_bravo}"}
    bravo_incidents = client.get("/v1/incidents?tenant_id=rural-isp-bravo", headers=headers_bravo).json()
    bravo_inc_id = bravo_incidents["incidents"][0]["incident_id"]

    # 2. Login as user of rural-isp-alpha
    auth_alpha = client.post(
        "/v1/auth/token",
        json={"username": "responder_alpha", "password": "FcsDemo2026!"},
    ).json()
    token_alpha = auth_alpha["access_token"]
    headers_alpha = {"Authorization": f"Bearer {token_alpha}"}

    # 3. Attempt to approve an action on bravo's incident using alpha credentials -> Must return 403
    resp = client.post(
        f"/v1/incidents/{bravo_inc_id}/actions",
        json={
            "action_type": "TEMPORARY_BLOCK",
            "target": "203.0.113.88",
            "duration_seconds": 600,
            "idempotency_key": "cross_tenant_malicious_key",
            "scope": "EDGE_FIREWALL",
        },
        headers=headers_alpha,
    )
    assert resp.status_code == 403
