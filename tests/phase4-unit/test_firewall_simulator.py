"""Unit tests for the isolated software firewall simulator."""

import time
from datetime import UTC, datetime

from fcs_api.database import get_db, reset_db, seed_demo_data
from fcs_api.firewall.simulator import FirewallSimulator


def setup_function():
    reset_db()
    seed_demo_data()


def create_test_action(action_id: str, tenant_id: str):
    now_str = datetime.now(UTC).isoformat()
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO incidents (
                incident_id, tenant_id, grouping_key, title, attack_category,
                severity, status, risk_score, target_ip, target_port, evidence_json,
                model_version, rule_matches_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "inc_dummy_fw_test", tenant_id, f"{tenant_id}:10.0.0.1:Test",
                "Firewall Test Incident", "Test", "LOW", "NEW", 0.5, "10.0.0.1", 80, "{}",
                "lightgbm_deployable_subset", "[]", now_str, now_str,
            ),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO action_journal (
                action_id, incident_id, tenant_id, approved_by, approval_timestamp,
                action_type, target, scope, duration_seconds, status, idempotency_key, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action_id, "inc_dummy_fw_test", tenant_id, "usr_test", now_str,
                "TEMPORARY_BLOCK", "10.0.0.1", "EDGE_FIREWALL", 300, "PENDING", f"idem_{action_id}", now_str,
            ),
        )


def test_firewall_apply_verify_and_revoke():
    tenant_id = "rural-isp-alpha"
    action_id = "act_unit_test_001"
    target = "203.0.113.199"

    create_test_action(action_id, tenant_id)

    # 1. Apply rule
    rule_res = FirewallSimulator.apply_rule(
        action_id=action_id,
        tenant_id=tenant_id,
        target=target,
        rule_type="TEMPORARY_BLOCK",
        duration_seconds=300,
        parameters={"scope": "EDGE_FIREWALL"},
    )
    assert rule_res["status"] == "ACTIVE"
    rule_id = rule_res["rule_id"]

    # 2. Verify rule exists via read-back
    is_verified = FirewallSimulator.verify_rule(rule_id, tenant_id)
    assert is_verified is True

    # 3. List active rules
    active_rules = FirewallSimulator.list_active_rules(tenant_id)
    assert any(r["rule_id"] == rule_id for r in active_rules)

    # 4. Revoke rule
    revoked = FirewallSimulator.revoke_rule(rule_id, tenant_id)
    assert revoked is True

    # 5. Verify rule is no longer active
    active_after = FirewallSimulator.list_active_rules(tenant_id)
    assert not any(r["rule_id"] == rule_id for r in active_after)


def test_firewall_rule_expiration():
    tenant_id = "rural-isp-alpha"
    action_id = "act_unit_test_expire"
    target = "203.0.113.200"

    create_test_action(action_id, tenant_id)

    # Apply 1-second rule
    rule_res = FirewallSimulator.apply_rule(
        action_id=action_id,
        tenant_id=tenant_id,
        target=target,
        rule_type="TEMPORARY_BLOCK",
        duration_seconds=1,
    )
    rule_id = rule_res["rule_id"]

    # Wait for expiration
    time.sleep(1.2)

    # Run expiration check
    expired_count = FirewallSimulator.expire_stale_rules()
    assert expired_count >= 1

    # Verify rule is expired
    is_still_active = FirewallSimulator.verify_rule(rule_id, tenant_id)
    assert is_still_active is False
