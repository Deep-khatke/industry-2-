"""End-to-end integration tests for FCS-HMD Hierarchical Threat Detection pipeline."""

import json

import pytest
from fastapi.testclient import TestClient
from fcs_api.app import app
from fcs_api.database import reset_db, seed_demo_data
from fcs_api.detection.service import DetectionService
from fcs_api.incidents.manager import IncidentManager


@pytest.fixture(scope="module")
def client():
    reset_db()
    seed_demo_data()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def auth_headers(client):
    login_res = client.post(
        "/v1/auth/token",
        json={"username": "admin_alpha", "password": "FcsDemo2026!"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_hmd_endpoints_and_bundle_inspection(client, auth_headers):
    # 1. Inspect detection bundle
    bundle_res = client.get("/v1/detection/bundle", headers=auth_headers)
    assert bundle_res.status_code == 200
    bundle_data = bundle_res.json()
    assert bundle_data["bundle_id"] == "fcs-hmd-bundle-v1"
    assert "lightgbm_deployable_subset" in bundle_data["general_model_id"]
    assert "isolationforest_anomaly_tenant" in bundle_data["anomaly_model_id"]
    assert "lightgbm_ddos_specialist" in bundle_data["specialist_model_ids"]

    # 2. Inspect registered models
    models_res = client.get("/v1/detection/models", headers=auth_headers)
    assert models_res.status_code == 200
    model_ids = [m["model_id"] for m in models_res.json()]
    assert "isolationforest_anomaly_tenant" in model_ids
    assert "lightgbm_ddos_specialist" in model_ids

    # 3. Inspect ISP anomaly status
    isp_res = client.get("/v1/detection/isp-anomaly-status", headers=auth_headers)
    assert isp_res.status_code == 200
    assert isp_res.json()["tenant_id"] == "rural-isp-alpha"
    assert isp_res.json()["isolation_boundary"] == "STRICT_PER_TENANT"


def test_e2e_volumetric_ddos_hierarchical_detection(client, auth_headers):
    det_service = DetectionService()

    # Create a volumetric window that triggers Level 1 and DDoS specialist
    burst_window = {
        "window_id": "test_win_ddos_e2e",
        "tenant_id": "rural-isp-alpha",
        "flow_count": 80,
        "feature_vector": {
            "L4_SRC_PORT": 44444,
            "L4_DST_PORT": 80,
            "PROTOCOL": 6,
            "IN_BYTES": 950_000,
            "IN_PKTS": 4_000,
            "OUT_BYTES": 100,
            "OUT_PKTS": 2,
            "FLOW_DURATION_MILLISECONDS": 200.0,
            "TCP_FLAGS": 24,
            "SRC_TO_DST_SECOND_BYTES": 4_750_000.0,
            "SRC_TO_DST_AVG_THROUGHPUT": 4_750_000.0,
        },
    }

    result = det_service.analyze_window(burst_window)
    assert result["is_threat"] is True
    assert result["risk_score"] >= 0.70
    assert "multi_model_evidence" in result
    evidence = result["multi_model_evidence"]
    assert "general_score" in evidence
    assert "anomaly_score" in evidence
    assert "specialist_scores" in evidence
    assert "routing_decision" in evidence
    assert result["ml_inference"]["network_action_executed"] is False

    # Process incident creation
    inc = IncidentManager.process_detection(result, window_data=burst_window)
    assert inc is not None
    incident_id = inc["incident_id"]

    # Verify incident contains multi_model_evidence via API
    inc_res = client.get(f"/v1/incidents/{incident_id}", headers=auth_headers)
    assert inc_res.status_code == 200
    inc_data = inc_res.json()
    assert inc_data["incident_id"] == incident_id
    stored_evidence = json.loads(inc_data["evidence_json"])
    assert "multi_model_evidence" in stored_evidence
    assert stored_evidence["multi_model_evidence"]["fusion_method"] is not None

    # Verify routing decision was recorded
    routes_res = client.get("/v1/detection/routing-decisions?limit=10", headers=auth_headers)
    assert routes_res.status_code == 200
    assert len(routes_res.json()) > 0
