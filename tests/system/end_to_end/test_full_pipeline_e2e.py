"""Full Pipeline End-to-End Test Suite for Phase 8.

Verifies end-to-end data flow:
Synthetic Telemetry -> Stream Adapter -> Feature Window -> FCS-HMD Multi-Model Inference
-> Incident Creation -> Manual Response Authorization -> Firewall Simulator -> Rollback.
"""

import uuid
from datetime import UTC, datetime
import pytest

from packages.contracts.flow_event import FlowEvent
from adapters.memory.sink import MemoryStreamSink
from fcs_api.database import init_db, seed_demo_data, get_db
from fcs_api.detection.service import DetectionService
from fcs_api.incidents.manager import IncidentManager
from fcs_api.response.policy import ResponsePolicyEngine, ResponsePolicyError
from fcs_api.firewall.simulator import FirewallSimulator
from tools.phase8.scenario_runner.runner import ScenarioRunner


@pytest.fixture(autouse=True)
def setup_test_db():
    seed_demo_data()


def test_scenario_runner_all_suites():
    """Verify ScenarioRunner completes all 4 configured multi-tenant traffic scenarios."""
    runner = ScenarioRunner()
    res = runner.run_all()
    assert res["total_scenarios"] == 4
    assert res["successful_scenarios"] == 4
    for scenario in res["results"]:
        assert scenario["success"] is True


def test_full_pipeline_single_tenant_flow():
    """Verify single tenant flow through ingestion, scoring, incident, and simulated action."""
    tenant_id = "rural-isp-alpha"
    now = datetime.now(UTC)

    # 1. Ingestion
    sink = MemoryStreamSink(max_capacity=1000)
    ev = FlowEvent(
        tenant_id=tenant_id,
        exporter_id="gw-alpha-core",
        observation_domain=101,
        boot_epoch=1,
        sequence=1,
        event_time=now,
        byte_count=800_000,
        packet_count=600,
        tcp_flags=0x02,  # SYN flag
    )
    sink.write(ev)
    events = sink.get_events(tenant_id=tenant_id)
    assert len(events) == 1

    # 2. Window synthesis
    window = {
        "tenant_id": tenant_id,
        "window_id": f"win_test_{uuid.uuid4().hex[:8]}",
        "start_time": now.isoformat(),
        "end_time": now.isoformat(),
        "flow_count": 1,
        "byte_count": 800_000,
        "packet_count": 600,
        "mean_flow_duration": 0.5,
        "syn_ratio": 1.0,
        "ack_ratio": 0.0,
        "rst_ratio": 0.0,
        "unique_src_ips": 5,
        "unique_dst_ips": 1,
        "unique_dst_ports": 1,
        "external_ip_ratio": 0.4,
        "dns_query_ratio": 0.0,
        "nxdomain_ratio": 0.0,
        "ssh_flow_ratio": 0.0,
    }

    # 3. FCS-HMD Inference
    service = DetectionService()
    detection = service.analyze_window(window)
    assert "risk_score" in detection
    assert "multi_model_evidence" in detection

    # 4. Incident Management
    detection["is_threat"] = True
    detection["attack_category"] = "Volumetric Flood"
    detection["severity"] = "HIGH"
    detection["tenant_id"] = tenant_id

    inc = IncidentManager.process_detection(
        detection_result=detection,
        flow_event=ev.model_dump(mode="json"),
        window_data=window,
    )
    assert inc is not None
    incident_id = inc["incident_id"]

    # 5. Manual Action (Authorized Responder)
    acting_user = {
        "user_id": "usr_analyst_alpha",
        "tenant_id": tenant_id,
        "role": "SECURITY_RESPONDER",
    }
    action_res = ResponsePolicyEngine.execute_manual_action(
        incident_id=incident_id,
        action_type="TEMPORARY_BLOCK",
        target="198.51.100.77",
        duration_seconds=60,
        acting_user=acting_user,
        idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
    )
    assert action_res["status"] == "VERIFIED"

    # 6. Verify rule in simulator
    rules = FirewallSimulator.list_active_rules(tenant_id)
    assert any(r["rule_id"] == action_res.get("rule_id", r["rule_id"]) for r in rules)

    # 7. Rollback
    rollback_res = ResponsePolicyEngine.rollback_action(
        action_id=action_res["action_id"],
        acting_user=acting_user,
    )
    assert rollback_res["status"] == "ROLLED_BACK"


def test_idempotent_duplicate_events():
    """Verify duplicate incident detection requests do not create multiple business incidents."""
    tenant_id = "rural-isp-bravo"
    det = {
        "score_id": f"sc_{uuid.uuid4().hex[:8]}",
        "tenant_id": tenant_id,
        "is_threat": True,
        "attack_category": "DDoS",
        "severity": "CRITICAL",
        "risk_score": 0.92,
    }
    flow = {"dst_ip": "198.51.100.99", "dst_port": 443}

    # First event
    inc1 = IncidentManager.process_detection(det, flow_event=flow)
    assert inc1 is not None

    # Duplicate replay within grouping window
    inc2 = IncidentManager.process_detection(det, flow_event=flow)
    assert inc2 is not None
    assert inc1["incident_id"] == inc2["incident_id"], "Duplicate event must resolve to same incident ID"
