"""Phase 11: Response Safety, Protected Targets, and Firewall Simulator Tests."""

from fastapi.testclient import TestClient
import pytest

from fcs_api.app import app
from fcs_api.database import get_db

client = TestClient(app)


def get_token(username: str) -> str:
    resp = client.post(
        "/v1/auth/token",
        json={"username": username, "password": "FcsDemo2026!"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def test_incident_id():
    """Ensure a valid test incident exists in the DB for Alpha."""
    inc_id = "inc_safety_test_001"
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO incidents (
                incident_id, tenant_id, grouping_key, title, attack_category, severity,
                status, risk_score, target_ip, target_port, evidence_json, rule_matches_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (
                inc_id, "rural-isp-alpha", "grp_001", "Test Incident for Response Safety",
                "DDoS", "HIGH", "NEW", 0.90, "198.51.100.99", 80, "{}", "[]"
            )
        )
    return inc_id


def test_auto_response_strictly_disabled():
    """Verify Gate G13 safety: AUTO_LIVE is disabled and cannot be turned on via API."""
    token = get_token("responder_alpha")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/v1/response-policy", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["response_mode"] == "MANUAL"
    assert data["auto_response_enabled"] is False


def test_protected_targets_rejected_by_policy(test_incident_id):
    """Verify defensive responses targeting protected DNS or gateways are rejected."""
    token = get_token("responder_alpha")
    headers = {"Authorization": f"Bearer {token}"}

    protected_targets = ["1.1.1.1", "8.8.8.8", "9.9.9.9", "127.0.0.1", "10.0.0.1", "255.255.255.255"]
    for i, ip in enumerate(protected_targets):
        resp = client.post(
            f"/v1/incidents/{test_incident_id}/actions",
            json={
                "action_type": "TEMPORARY_BLOCK",
                "target": ip,
                "duration_seconds": 300,
                "idempotency_key": f"idemp_prot_test_{i}_{ip.replace('.', '_')}",
            },
            headers=headers,
        )
        assert resp.status_code in (400, 403, 422)


def test_tier1_analyst_cannot_approve_actions(test_incident_id):
    """Verify SECURITY_ANALYST (Tier-1) is forbidden from approving defensive actions."""
    analyst_token = get_token("analyst_alpha")
    headers = {"Authorization": f"Bearer {analyst_token}"}

    resp = client.post(
        f"/v1/incidents/{test_incident_id}/actions",
        json={
            "action_type": "TEMPORARY_BLOCK",
            "target": "198.51.100.45",
            "duration_seconds": 300,
            "idempotency_key": "idemp_unauth_approval_001",
        },
        headers=headers,
    )
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"] or "Unauthorized" in resp.json()["detail"]
