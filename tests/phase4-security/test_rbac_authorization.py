"""Security tests for Role-Based Access Control (RBAC)."""

from fastapi.testclient import TestClient
from fcs_api.app import app
from fcs_api.database import reset_db, seed_demo_data
from fcs_api.telemetry.replay import ReplayCoordinator

client = TestClient(app)


def setup_function():
    reset_db()
    seed_demo_data()


def test_read_only_role_cannot_modify_incidents():
    # 1. Create an incident in alpha
    ReplayCoordinator.run_scenario("suspicious", tenant_id="rural-isp-alpha")

    # 2. Login as viewer_alpha (READ_ONLY role)
    auth_ro = client.post(
        "/v1/auth/token",
        json={"username": "viewer_alpha", "password": "FcsDemo2026!"},
    ).json()
    token_ro = auth_ro["access_token"]
    headers_ro = {"Authorization": f"Bearer {token_ro}"}

    # Can view incidents
    inc_resp = client.get("/v1/incidents?tenant_id=rural-isp-alpha", headers=headers_ro)
    assert inc_resp.status_code == 200
    inc_id = inc_resp.json()["incidents"][0]["incident_id"]

    # CANNOT patch incident status -> 403
    patch_resp = client.patch(
        f"/v1/incidents/{inc_id}",
        json={"status": "INVESTIGATING", "notes": "Unauthorized attempt by read-only user"},
        headers=headers_ro,
    )
    assert patch_resp.status_code == 403


def test_security_analyst_cannot_approve_defensive_actions():
    # 1. Create incident in alpha
    ReplayCoordinator.run_scenario("suspicious", tenant_id="rural-isp-alpha")

    # 2. Login as analyst_alpha
    auth_analyst = client.post(
        "/v1/auth/token",
        json={"username": "analyst_alpha", "password": "FcsDemo2026!"},
    ).json()
    token_analyst = auth_analyst["access_token"]
    headers_analyst = {"Authorization": f"Bearer {token_analyst}"}

    # Can update incident status to INVESTIGATING
    inc_list = client.get("/v1/incidents?tenant_id=rural-isp-alpha", headers=headers_analyst).json()
    inc_id = inc_list["incidents"][0]["incident_id"]
    patch_resp = client.patch(f"/v1/incidents/{inc_id}", json={"status": "INVESTIGATING"}, headers=headers_analyst)
    assert patch_resp.status_code == 200

    # CANNOT approve manual defensive action -> 403 Forbidden
    act_resp = client.post(
        f"/v1/incidents/{inc_id}/actions",
        json={
            "action_type": "TEMPORARY_BLOCK",
            "target": "203.0.113.88",
            "duration_seconds": 600,
            "idempotency_key": "analyst_escalation_attempt",
            "scope": "EDGE_FIREWALL",
        },
        headers=headers_analyst,
    )
    assert act_resp.status_code == 403
    assert "Unauthorized" in act_resp.json()["detail"]
