"""End-to-end integration test demonstrating complete Phase 4 workflow.

Workflow:
Telemetry / Replay
→ Flow Ingestion
→ Window Aggregation
→ ML Inference + Rules
→ Threat Scoring
→ Incident Creation & Storage
→ Defensive Recommendation
→ Human Administrator Approval
→ Software Firewall Simulator Execution
→ Read-back Verification
→ Rollback & Audit Record
"""

import uuid
from datetime import UTC, datetime

from fcs_api.database import reset_db, seed_demo_data
from fcs_api.incidents.manager import IncidentManager
from fcs_api.response.policy import ResponsePolicyEngine
from fcs_api.telemetry.ingest import TelemetryIngestionPipeline


def setup_function():
    reset_db()
    seed_demo_data()


def test_full_autonomous_cyber_defense_pipeline():
    tenant_id = "rural-isp-alpha"
    now_str = datetime.now(UTC).isoformat()
    pipeline = TelemetryIngestionPipeline()

    # 1. Ingest a burst of volumetric flood flows (DDoS)
    target_victim_ip = "198.51.100.88"
    for i in range(35):
        raw_flow = {
            "event_id": f"fl_e2e_{uuid.uuid4().hex[:8]}",
            "tenant_id": tenant_id,
            "exporter_id": "exp-alpha-core1",
            "src_ip": f"203.0.113.{100 + i}",
            "dst_ip": target_victim_ip,
            "src_port": 50000 + i,
            "dst_port": 443,
            "protocol": "TCP",
            "protocol_num": 6,
            "byte_count": 60_000,
            "packet_count": 500,
            "flow_duration_ms": 500.0,
            "tcp_flags": 16,  # ACK flood
            "event_time": now_str,
        }
        res = pipeline.ingest_record(raw_flow)
        assert res["status"] == "PROCESSED"

    # 2. Verify an incident was created in database and deduplicated
    incidents = IncidentManager.list_incidents(tenant_id=tenant_id)
    assert len(incidents) >= 1
    ddos_inc = next((inc for inc in incidents if inc["attack_category"] == "DDoS"), None)
    assert ddos_inc is not None
    assert ddos_inc["severity"] in ("CRITICAL", "HIGH")
    assert ddos_inc["target_ip"] == target_victim_ip
    incident_id = ddos_inc["incident_id"]

    # 3. Verify recommendation was generated
    recs = IncidentManager.get_recommendations(incident_id)
    assert len(recs) >= 1
    rec = recs[0]
    assert rec["action_type"] in ("TEMPORARY_BLOCK", "RATE_LIMIT")

    # 4. Human Administrator reviews and approves Manual Action
    responder_user = {
        "user_id": "usr_responder_alpha",
        "username": "responder_alpha",
        "tenant_id": tenant_id,
        "role": "SECURITY_RESPONDER",
    }
    idempotency_key = f"e2e_idem_{uuid.uuid4().hex[:10]}"

    action_res = ResponsePolicyEngine.execute_manual_action(
        incident_id=incident_id,
        action_type=rec["action_type"],
        target="203.0.113.100",  # Attacker bot
        duration_seconds=900,
        acting_user=responder_user,
        idempotency_key=idempotency_key,
        scope=rec["scope"],
        recommendation_id=rec["recommendation_id"],
    )

    # 5. Verify simulated execution and read-back verification state
    assert action_res["status"] == "VERIFIED"
    assert "Simulated defensive action" in action_res["disclaimer"]
    action_id = action_res["action_id"]

    # 6. Verify incident status was updated to MITIGATED
    updated_inc = IncidentManager.get_incident(incident_id)
    assert updated_inc is not None
    assert updated_inc["status"] == "MITIGATED"

    # 7. Verify action rollback capability
    rollback_res = ResponsePolicyEngine.rollback_action(action_id=action_id, acting_user=responder_user)
    assert rollback_res["status"] == "ROLLED_BACK"

    # 8. Check audit trail
    history = IncidentManager.get_history(incident_id)
    assert len(history) >= 1
    assert any(h["new_status"] == "MITIGATED" for h in history)
