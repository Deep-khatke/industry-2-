"""Phase 11: End-to-End Release Candidate Integrated Verification Test."""

import importlib.util
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from fcs_api.app import app

# Load zero cost scanner dynamically from tools/zero-cost-audit/scanner.py
_scanner_path = Path(__file__).resolve().parents[3] / "tools" / "zero-cost-audit" / "scanner.py"
_spec = importlib.util.spec_from_file_location("zero_cost_scanner", str(_scanner_path))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
ZeroCostScanner = _mod.ZeroCostScanner

client = TestClient(app)


def test_complete_end_to_end_release_candidate_workflow():
    """Executes the full 15-step integrated development release candidate workflow."""
    # 1. Verify backend health
    health_resp = client.get("/healthz")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"
    assert health_resp.json()["zero_cost_enforced"] is True

    # 2. Authenticate
    auth_resp = client.post(
        "/v1/auth/token",
        json={"username": "responder_alpha", "password": "FcsDemo2026!"},
    )
    assert auth_resp.status_code == 200
    token = auth_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Verify user identity
    me_resp = client.get("/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["tenant_id"] == "rural-isp-alpha"

    # 4. Trigger synthetic flow replay (Suspicious DDoS burst)
    replay_resp = client.post(
        "/v1/dev/replay/start",
        json={"scenario": "suspicious", "tenant_id": "rural-isp-alpha"},
        headers=headers,
    )
    assert replay_resp.status_code == 200
    replay_data = replay_resp.json()
    assert replay_data["processed_count"] > 0
    assert replay_data["incidents_created"] > 0

    # 5. Verify incident persistence
    incidents_resp = client.get("/v1/incidents?tenant_id=rural-isp-alpha", headers=headers)
    assert incidents_resp.status_code == 200
    inc_list = incidents_resp.json().get("incidents", [])
    assert len(inc_list) > 0

    # 6. Verify detection status & HMD model health
    det_resp = client.get("/v1/detection/status", headers=headers)
    assert det_resp.status_code == 200
    assert det_resp.json()["detection_mode"] == "HYBRID_ML_RULES"

    # 7. Verify cross-tenant access rejection (IDOR protection)
    cross_resp = client.get("/v1/incidents?tenant_id=rural-isp-bravo", headers=headers)
    assert cross_resp.status_code == 403

    # 8. Check response policy profile (MANUAL default, AUTO_LIVE disabled)
    policy_resp = client.get("/v1/response-policy", headers=headers)
    assert policy_resp.status_code == 200
    assert policy_resp.json()["response_mode"] == "MANUAL"
    assert policy_resp.json()["auto_response_enabled"] is False

    # 9. Verify zero-cost compliance across codebase
    scanner = ZeroCostScanner()
    compliance_report = scanner.run_scan()
    assert compliance_report["status"] == "PASS"
    assert compliance_report["violations_found"] == 0
