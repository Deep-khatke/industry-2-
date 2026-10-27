"""Security tests for defensive response policy safety boundaries (G08 Release Gate)."""

from fastapi.testclient import TestClient
from fcs_api.app import app
from fcs_api.database import reset_db, seed_demo_data
from fcs_api.telemetry.replay import ReplayCoordinator

client = TestClient(app)


def setup_function():
    reset_db()
    seed_demo_data()


def test_protected_target_rejection():
    # 1. Create incident
    ReplayCoordinator.run_scenario("suspicious", tenant_id="rural-isp-alpha")

    # 2. Login as responder_alpha
    auth = client.post(
        "/v1/auth/token",
        json={"username": "responder_alpha", "password": "FcsDemo2026!"},
    ).json()
    token = auth["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    inc_list = client.get("/v1/incidents?tenant_id=rural-isp-alpha", headers=headers).json()
    inc_id = inc_list["incidents"][0]["incident_id"]

    # Attempt to block protected loopback 127.0.0.1
    resp = client.post(
        f"/v1/incidents/{inc_id}/actions",
        json={
            "action_type": "TEMPORARY_BLOCK",
            "target": "127.0.0.1",
            "duration_seconds": 600,
            "idempotency_key": "protected_target_attempt_01",
            "scope": "EDGE_FIREWALL",
        },
        headers=headers,
    )
    assert resp.status_code == 400
    assert "protected infrastructure" in resp.json()["detail"]

    # Attempt to block default route 0.0.0.0/0
    resp_all = client.post(
        f"/v1/incidents/{inc_id}/actions",
        json={
            "action_type": "TEMPORARY_BLOCK",
            "target": "0.0.0.0/0",
            "duration_seconds": 600,
            "idempotency_key": "protected_target_attempt_02",
            "scope": "EDGE_FIREWALL",
        },
        headers=headers,
    )
    assert resp_all.status_code == 400


def test_action_duration_bounds_enforced():
    # Login as responder
    auth = client.post("/v1/auth/token", json={"username": "responder_alpha", "password": "FcsDemo2026!"}).json()
    token = auth["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ReplayCoordinator.run_scenario("suspicious", tenant_id="rural-isp-alpha")
    inc_id = client.get("/v1/incidents?tenant_id=rural-isp-alpha", headers=headers).json()["incidents"][0]["incident_id"]

    # Duration too short (< 60s)
    resp_short = client.post(
        f"/v1/incidents/{inc_id}/actions",
        json={
            "action_type": "TEMPORARY_BLOCK",
            "target": "203.0.113.88",
            "duration_seconds": 10,
            "idempotency_key": "duration_too_short",
        },
        headers=headers,
    )
    assert resp_short.status_code in (400, 422)

    # Duration too long (> 3600s, permanent block attempt)
    resp_long = client.post(
        f"/v1/incidents/{inc_id}/actions",
        json={
            "action_type": "TEMPORARY_BLOCK",
            "target": "203.0.113.88",
            "duration_seconds": 86400,
            "idempotency_key": "permanent_block_attempt",
        },
        headers=headers,
    )
    assert resp_long.status_code in (400, 422)


def test_idempotency_conflict_rejection():
    auth = client.post("/v1/auth/token", json={"username": "responder_alpha", "password": "FcsDemo2026!"}).json()
    token = auth["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ReplayCoordinator.run_scenario("suspicious", tenant_id="rural-isp-alpha")
    inc_id = client.get("/v1/incidents?tenant_id=rural-isp-alpha", headers=headers).json()["incidents"][0]["incident_id"]

    idempotency_key = "unique_idem_key_999"

    # First call succeeds
    r1 = client.post(
        f"/v1/incidents/{inc_id}/actions",
        json={
            "action_type": "TEMPORARY_BLOCK",
            "target": "203.0.113.88",
            "duration_seconds": 600,
            "idempotency_key": idempotency_key,
        },
        headers=headers,
    )
    assert r1.status_code == 200

    # Conflicting reuse of same idempotency key for different target fails
    r2 = client.post(
        f"/v1/incidents/{inc_id}/actions",
        json={
            "action_type": "TEMPORARY_BLOCK",
            "target": "203.0.113.99",  # Different target!
            "duration_seconds": 600,
            "idempotency_key": idempotency_key,
        },
        headers=headers,
    )
    assert r2.status_code == 400
    assert "Idempotency conflict" in r2.json()["detail"]
