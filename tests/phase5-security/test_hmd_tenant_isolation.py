"""Security tests verifying tenant isolation in FCS-HMD inference, routing, and anomaly baselines."""

import pytest
from fastapi.testclient import TestClient
from fcs_api.app import app
from fcs_api.database import reset_db, seed_demo_data


@pytest.fixture(scope="module")
def client():
    reset_db()
    seed_demo_data()
    with TestClient(app) as test_client:
        yield test_client


def get_token(client, username, password):
    res = client.post("/v1/auth/token", json={"username": username, "password": password})
    return res.json()["access_token"]


def test_cross_tenant_routing_decisions_isolation(client):
    alpha_token = get_token(client, "analyst_alpha", "FcsDemo2026!")
    bravo_token = get_token(client, "analyst_bravo", "FcsDemo2026!")

    # Request routing decisions as alpha
    alpha_res = client.get("/v1/detection/routing-decisions", headers={"Authorization": f"Bearer {alpha_token}"})
    assert alpha_res.status_code == 200
    for item in alpha_res.json():
        assert item["tenant_id"] == "rural-isp-alpha"

    # Request routing decisions as bravo
    bravo_res = client.get("/v1/detection/routing-decisions", headers={"Authorization": f"Bearer {bravo_token}"})
    assert bravo_res.status_code == 200
    for item in bravo_res.json():
        assert item["tenant_id"] == "rural-isp-bravo"


def test_tenant_anomaly_status_scoping(client):
    alpha_token = get_token(client, "analyst_alpha", "FcsDemo2026!")
    bravo_token = get_token(client, "analyst_bravo", "FcsDemo2026!")

    alpha_res = client.get("/v1/detection/isp-anomaly-status", headers={"Authorization": f"Bearer {alpha_token}"})
    assert alpha_res.status_code == 200
    assert alpha_res.json()["tenant_id"] == "rural-isp-alpha"
    assert alpha_res.json()["cross_tenant_access"] == "BLOCKED"

    bravo_res = client.get("/v1/detection/isp-anomaly-status", headers={"Authorization": f"Bearer {bravo_token}"})
    assert bravo_res.status_code == 200
    assert bravo_res.json()["tenant_id"] == "rural-isp-bravo"
    assert bravo_res.json()["cross_tenant_access"] == "BLOCKED"
