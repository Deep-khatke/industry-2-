"""Integration tests for reproducible demonstration replay scenarios."""

from fcs_api.database import reset_db, seed_demo_data
from fcs_api.incidents.manager import IncidentManager
from fcs_api.telemetry.replay import ReplayCoordinator


def setup_function():
    reset_db()
    seed_demo_data()


def test_scenario_normal_no_false_alarms():
    res = ReplayCoordinator.run_scenario("normal", tenant_id="rural-isp-alpha")
    assert res["scenario"] == "normal"
    assert res["replayed_flows"] == 25

    # Benign flows must NOT generate incidents
    incidents = IncidentManager.list_incidents("rural-isp-alpha")
    assert len(incidents) == 0, "Benign normal traffic must not create false positive incidents"


def test_scenario_suspicious_ddos():
    res = ReplayCoordinator.run_scenario("suspicious", tenant_id="rural-isp-alpha")
    assert res["scenario"] == "suspicious"
    assert res["replayed_flows"] == 40

    incidents = IncidentManager.list_incidents("rural-isp-alpha")
    assert len(incidents) >= 1
    ddos_inc = next((i for i in incidents if i["attack_category"] == "DDoS"), None)
    assert ddos_inc is not None
    assert ddos_inc["severity"] in ("CRITICAL", "HIGH")


def test_scenario_scanning_recon():
    res = ReplayCoordinator.run_scenario("scanning", tenant_id="rural-isp-alpha")
    assert res["scenario"] == "scanning"
    assert res["replayed_flows"] == 16

    incidents = IncidentManager.list_incidents("rural-isp-alpha")
    assert len(incidents) >= 1
    scan_inc = next((i for i in incidents if i["attack_category"] in ("PortScan", "Reconnaissance")), None)
    assert scan_inc is not None
    assert scan_inc["severity"] in ("MEDIUM", "HIGH", "CRITICAL")
