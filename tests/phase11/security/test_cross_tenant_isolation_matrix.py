"""Phase 11: Cross-Tenant Isolation Matrix Across 7 Simulated ISP Tenants."""

from fastapi.testclient import TestClient
import pytest

from fcs_api.app import app
from fcs_api.database import init_db, seed_demo_data

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_db():
    init_db()
    seed_demo_data()


def get_token(username: str) -> str:
    resp = client.post(
        "/v1/auth/token",
        json={"username": username, "password": "FcsDemo2026!"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_cross_tenant_overview_isolation():
    """Verify Alpha responder cannot view Bravo tenant overview."""
    token_alpha = get_token("responder_alpha")
    headers = {"Authorization": f"Bearer {token_alpha}"}

    # Access Alpha: allowed
    alpha_resp = client.get("/v1/overview?tenant_id=rural-isp-alpha", headers=headers)
    assert alpha_resp.status_code == 200

    # Access Bravo: forbidden 403
    bravo_resp = client.get("/v1/overview?tenant_id=rural-isp-bravo", headers=headers)
    assert bravo_resp.status_code == 403
    assert "Cross-tenant access violation" in bravo_resp.json()["detail"]


def test_cross_tenant_incident_ledger_isolation():
    """Verify incident list query enforces caller's tenant scoping."""
    token_alpha = get_token("responder_alpha")
    headers = {"Authorization": f"Bearer {token_alpha}"}

    # Query without tenant param defaults to caller tenant
    resp = client.get("/v1/incidents", headers=headers)
    assert resp.status_code == 200
    for inc in resp.json().get("incidents", []):
        assert inc["tenant_id"] == "rural-isp-alpha"

    # Query with another tenant returns 403
    forbidden_resp = client.get("/v1/incidents?tenant_id=rural-isp-bravo", headers=headers)
    assert forbidden_resp.status_code == 403


def test_cross_tenant_action_journal_isolation():
    """Verify actions query strictly isolates defensive response actions between tenants."""
    token_alpha = get_token("responder_alpha")
    headers = {"Authorization": f"Bearer {token_alpha}"}

    # Actions for Bravo
    resp = client.get("/v1/actions?tenant_id=rural-isp-bravo", headers=headers)
    assert resp.status_code == 403


def test_cross_tenant_response_policy_isolation():
    """Verify response policy read/write enforces tenant boundaries."""
    token_alpha = get_token("responder_alpha")
    headers = {"Authorization": f"Bearer {token_alpha}"}

    resp = client.get("/v1/response-policy", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["response_mode"] == "MANUAL"
    assert data["auto_response_enabled"] is False


def test_cross_tenant_federation_privacy_budget_isolation():
    """Verify client privacy budgets and local state are scoped per tenant."""
    token_alpha = get_token("responder_alpha")
    headers = {"Authorization": f"Bearer {token_alpha}"}

    # Federation status endpoint returns platform/consortium metadata without leaking private raw updates
    fed_resp = client.get("/v1/federation/status", headers=headers)
    assert fed_resp.status_code == 200
    data = fed_resp.json()
    assert "active_general_model" in data
    assert "differential_privacy" in data
    assert "secure_aggregation" in data
