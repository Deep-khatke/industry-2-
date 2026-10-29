"""Phase 11: API Contracts, Security Headers, and Prometheus Metrics Tests."""

from fastapi.testclient import TestClient

from fcs_api.app import app

client = TestClient(app)


def test_security_headers_present_on_all_responses():
    """Verify mandatory security headers and correlation ID are set on responses."""
    resp = client.get("/healthz")
    assert resp.status_code == 200

    headers = resp.headers
    assert "x-request-id" in headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert "default-src 'self'" in headers.get("content-security-policy", "")


def test_prometheus_metrics_endpoint():
    """Verify /metrics returns Prometheus format plain text metrics."""
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")

    body = resp.text
    assert "fcs_platform_info{" in body
    assert "fcs_active_tenants" in body
    assert "fcs_active_incidents" in body
    assert "fcs_zero_cost_enforced 1" in body


def test_healthz_endpoint_contract():
    """Verify /healthz adheres to system health contract."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "ok"
    assert data["version"] == "1.2.0"
    assert data["mode"] == "MANUAL"
    assert data["auto_response_enabled"] is False
    assert data["zero_cost_enforced"] is True
