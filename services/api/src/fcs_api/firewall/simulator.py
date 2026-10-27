"""Isolated software firewall simulator for zero-cost defensive response testing."""

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from ..database import get_db

SIMULATION_DISCLAIMER = "Simulated defensive action — no real network device modified."


class FirewallSimulator:
    """
    Isolated software firewall simulator.
    Applies simulated temporary blocks and rate-limits, provides state verification,
    rule expiry, and rollback without modifying any real network devices.
    """

    @classmethod
    def apply_rule(
        cls,
        action_id: str,
        tenant_id: str,
        target: str,
        rule_type: str,
        duration_seconds: int,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Apply a simulated defensive firewall rule."""
        rule_id = f"fw_{uuid.uuid4().hex[:12]}"
        now_dt = datetime.now(UTC)
        expires_dt = now_dt + timedelta(seconds=duration_seconds)
        now_str = now_dt.isoformat()
        expires_str = expires_dt.isoformat()

        params = parameters or {"scope": "EDGE_FIREWALL", "priority": 100}
        params["disclaimer"] = SIMULATION_DISCLAIMER

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO simulated_firewall_rules (
                    rule_id, action_id, tenant_id, target, rule_type,
                    parameters_json, applied_at, expires_at, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rule_id,
                    action_id,
                    tenant_id,
                    target,
                    rule_type,
                    json.dumps(params),
                    now_str,
                    expires_str,
                    "ACTIVE",
                    now_str,
                ),
            )

        return {
            "rule_id": rule_id,
            "action_id": action_id,
            "tenant_id": tenant_id,
            "target": target,
            "rule_type": rule_type,
            "applied_at": now_str,
            "expires_at": expires_str,
            "status": "ACTIVE",
            "disclaimer": SIMULATION_DISCLAIMER,
        }

    @classmethod
    def verify_rule(cls, rule_id: str, tenant_id: str) -> bool:
        """Verify that a simulated rule is committed in the active table and not expired."""
        now_str = datetime.now(UTC).isoformat()
        with get_db() as conn:
            row = conn.execute(
                """
                SELECT * FROM simulated_firewall_rules
                WHERE rule_id = ? AND tenant_id = ? AND status = 'ACTIVE' AND expires_at > ?
                """,
                (rule_id, tenant_id, now_str),
            ).fetchone()
            return row is not None

    @classmethod
    def revoke_rule(cls, rule_id: str, tenant_id: str) -> bool:
        """Revoke a simulated firewall rule (Rollback)."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM simulated_firewall_rules WHERE rule_id = ? AND tenant_id = ?",
                (rule_id, tenant_id),
            ).fetchone()
            if not row:
                return False

            conn.execute(
                "UPDATE simulated_firewall_rules SET status = 'REVOKED' WHERE rule_id = ?",
                (rule_id,),
            )
            return True

    @classmethod
    def list_active_rules(cls, tenant_id: str) -> list[dict[str, Any]]:
        """List currently active, non-expired simulated rules for a tenant."""
        now_str = datetime.now(UTC).isoformat()
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT * FROM simulated_firewall_rules
                WHERE tenant_id = ? AND status = 'ACTIVE' AND expires_at > ?
                ORDER BY created_at DESC
                """,
                (tenant_id, now_str),
            ).fetchall()
            return [dict(r) for r in rows]

    @classmethod
    def expire_stale_rules(cls) -> int:
        """Periodic cleanup task marking expired simulated rules as EXPIRED."""
        now_str = datetime.now(UTC).isoformat()
        with get_db() as conn:
            cursor = conn.execute(
                """
                UPDATE simulated_firewall_rules
                SET status = 'EXPIRED'
                WHERE status = 'ACTIVE' AND expires_at <= ?
                """,
                (now_str,),
            )
            return cursor.rowcount
