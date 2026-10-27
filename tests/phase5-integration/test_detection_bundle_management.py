"""Integration tests for DetectionBundle validation, authorized activation, and rollback."""

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


def test_bundle_authorized_activation_and_rollback(client):
    admin_token = get_token(client, "admin_alpha", "FcsDemo2026!")
    viewer_token = get_token(client, "viewer_alpha", "FcsDemo2026!")

    # Current active bundle
    cur_res = client.get("/v1/detection/bundle", headers={"Authorization": f"Bearer {admin_token}"})
    assert cur_res.status_code == 200
    orig_bundle = cur_res.json()

    # Unauthorized activation attempt by READ_ONLY user
    new_bundle_payload = dict(orig_bundle)
    new_bundle_payload["bundle_id"] = "fcs-hmd-bundle-v2-staging"
    new_bundle_payload["version"] = "1.2.1"

    unauth_res = client.post(
        "/v1/detection/bundle/activate",
        json=new_bundle_payload,
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    # Role error
    assert unauth_res.status_code == 403 or "not authorized" in unauth_res.text.lower()

    # Authorized activation by TENANT_ADMIN
    auth_res = client.post(
        "/v1/detection/bundle/activate",
        json=new_bundle_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert auth_res.status_code == 200
    assert auth_res.json()["success"] is True

    # Verify active bundle updated
    after_res = client.get("/v1/detection/bundle", headers={"Authorization": f"Bearer {admin_token}"})
    assert after_res.status_code == 200
    assert after_res.json()["bundle_id"] == "fcs-hmd-bundle-v2-staging"

    # Authorized rollback
    rollback_res = client.post(
        "/v1/detection/bundle/rollback",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert rollback_res.status_code == 200
    assert rollback_res.json()["success"] is True
    assert rollback_res.json()["active_bundle_id"] == "fcs-hmd-bundle-v1"

    # Verify restored bundle
    final_res = client.get("/v1/detection/bundle", headers={"Authorization": f"Bearer {admin_token}"})
    assert final_res.status_code == 200
    assert final_res.json()["bundle_id"] == "fcs-hmd-bundle-v1"


def test_tampered_bundle_rejected(client):
    admin_token = get_token(client, "admin_alpha", "FcsDemo2026!")

    # Bundle with non-existent model or fake digest
    tampered_bundle = {
        "bundle_id": "tampered_bundle",
        "version": "1.0.0",
        "general_model_id": "non_existent_model_id",
        "anomaly_model_id": "fake_anomaly",
        "specialist_model_ids": [],
        "model_hashes": {},
        "bundle_digest": "corrupted_digest",
        "authorized_by": "attacker",
        "status": "STAGING",
    }

    res = client.post(
        "/v1/detection/bundle/activate",
        json=tampered_bundle,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    assert res.json()["success"] is False
    assert "validation failed" in res.json()["message"].lower()
