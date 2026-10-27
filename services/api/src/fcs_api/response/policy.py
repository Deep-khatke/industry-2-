"""Manual Response Policy Engine and defensive safety validator."""

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from ..config import settings
from ..database import get_db
from ..firewall.simulator import FirewallSimulator
from ..incidents.manager import IncidentManager


class ResponsePolicyError(Exception):
    """Raised when an action request violates response safety policy."""


class ResponsePolicyEngine:
    """
    Validates defensive action requests against safety policies, verifies administrator
    authorization, enforces duration limits and target allowlists, and manages
    action journal auditing.
    """

    ALLOWED_ACTIONS = {"TEMPORARY_BLOCK", "RATE_LIMIT"}

    @classmethod
    def execute_manual_action(
        cls,
        incident_id: str,
        action_type: str,
        target: str,
        duration_seconds: int,
        acting_user: dict[str, Any],
        idempotency_key: str,
        scope: str = "EDGE_FIREWALL",
        recommendation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Validate and execute an authorized manual response action.
        Guarantees:
        1. Caller has SECURITY_RESPONDER or TENANT_ADMIN role.
        2. Incident belongs to caller's tenant.
        3. Target is not protected infrastructure.
        4. Duration is bounded (60s to 3600s). No permanent blocks.
        5. Idempotency key prevents duplicate execution.
        6. Simulated execution is verified via read-back.
        """
        tenant_id = acting_user.get("tenant_id")
        user_id = acting_user.get("user_id")
        user_role = acting_user.get("role")
        now_dt = datetime.now(UTC)
        now_str = now_dt.isoformat()

        # 1. Authorization check
        if user_role not in ("SECURITY_RESPONDER", "TENANT_ADMIN", "PLATFORM_ADMIN"):
            raise ResponsePolicyError(
                f"Unauthorized: Role '{user_role}' cannot approve defensive actions. Requires SECURITY_RESPONDER or TENANT_ADMIN."
            )

        # 2. Incident ownership check
        incident = IncidentManager.get_incident(incident_id, tenant_id=tenant_id)
        if not incident:
            any_inc = IncidentManager.get_incident(incident_id)
            if any_inc and any_inc.get("tenant_id") != tenant_id:
                raise ResponsePolicyError(
                    f"Unauthorized: Cross-tenant action rejected. Incident '{incident_id}' belongs to tenant '{any_inc.get('tenant_id')}'."
                )
            raise ResponsePolicyError(f"Incident '{incident_id}' not found for tenant '{tenant_id}'.")

        # 3. Action type validation
        if action_type not in cls.ALLOWED_ACTIONS:
            raise ResponsePolicyError(f"Invalid action type '{action_type}'. Allowed: {sorted(cls.ALLOWED_ACTIONS)}")

        # 4. Target safety validation (Protected infrastructure check)
        target_clean = target.strip()
        if target_clean in settings.protected_ip_ranges:
            raise ResponsePolicyError(
                f"Security Violation: Target '{target_clean}' is protected infrastructure and cannot be modified."
            )

        # 5. Duration bounds check (Strictly non-permanent)
        if duration_seconds < settings.min_action_duration_seconds or duration_seconds > settings.max_action_duration_seconds:
            raise ResponsePolicyError(
                f"Invalid duration: {duration_seconds}s is out of allowed range [{settings.min_action_duration_seconds}s, {settings.max_action_duration_seconds}s]."
            )

        # 6. Idempotency Key check
        with get_db() as conn:
            existing = conn.execute(
                "SELECT * FROM action_journal WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()

            if existing:
                # Return previously processed action if matching
                if existing["incident_id"] == incident_id and existing["target"] == target_clean:
                    return dict(existing)
                raise ResponsePolicyError(
                    f"Idempotency conflict: Key '{idempotency_key}' was previously used for a different action."
                )

        action_id = f"act_{uuid.uuid4().hex[:12]}"
        applied_time = now_str
        expiry_time = (now_dt + timedelta(seconds=duration_seconds)).isoformat()

        # 7. Record Action Journal in PENDING state first (satisfies FK in simulated_firewall_rules)
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO action_journal (
                    action_id, recommendation_id, incident_id, tenant_id,
                    approved_by, approval_timestamp, action_type, target,
                    scope, duration_seconds, applied_timestamp, expiry_timestamp,
                    status, idempotency_key, verification_details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action_id,
                    recommendation_id,
                    incident_id,
                    tenant_id,
                    user_id,
                    now_str,
                    action_type,
                    target_clean,
                    scope,
                    duration_seconds,
                    applied_time,
                    expiry_time,
                    "PENDING",
                    idempotency_key,
                    json.dumps({"state": "PENDING"}),
                    now_str,
                ),
            )

        # 8. Execute in Isolated Software Firewall Simulator
        fw_result = FirewallSimulator.apply_rule(
            action_id=action_id,
            tenant_id=tenant_id,
            target=target_clean,
            rule_type=action_type,
            duration_seconds=duration_seconds,
            parameters={"scope": scope, "incident_id": incident_id},
        )

        # 9. Simulator State Verification Read-back
        is_verified = FirewallSimulator.verify_rule(fw_result["rule_id"], tenant_id)
        action_status = "VERIFIED" if is_verified else "FAILED"

        # 10. Update Action Journal with verification result
        with get_db() as conn:
            conn.execute(
                """
                UPDATE action_journal
                SET status = ?, verification_details_json = ?
                WHERE action_id = ?
                """,
                (action_status, json.dumps(fw_result), action_id),
            )

            # Record audit event
            conn.execute(
                """
                INSERT INTO audit_events (
                    audit_id, tenant_id, actor_id, event_action,
                    resource_type, resource_id, details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"aud_{uuid.uuid4().hex[:12]}",
                    tenant_id,
                    user_id,
                    "ACTION_APPROVED_AND_EXECUTED",
                    "ACTION",
                    action_id,
                    json.dumps({"action_type": action_type, "target": target_clean, "status": action_status}),
                    now_str,
                ),
            )

        # 10. Update Incident status to MITIGATED
        if is_verified:
            IncidentManager.update_incident_status(
                incident_id=incident_id,
                new_status="MITIGATED",
                actor_id=user_id,
                notes=f"Simulated {action_type} applied to {target_clean} for {duration_seconds}s.",
                tenant_id=tenant_id,
            )

        return {
            "action_id": action_id,
            "incident_id": incident_id,
            "tenant_id": tenant_id,
            "approved_by": user_id,
            "action_type": action_type,
            "target": target_clean,
            "scope": scope,
            "duration_seconds": duration_seconds,
            "applied_timestamp": applied_time,
            "expiry_timestamp": expiry_time,
            "status": action_status,
            "is_verified": is_verified,
            "idempotency_key": idempotency_key,
            "disclaimer": fw_result["disclaimer"],
        }

    @classmethod
    def rollback_action(
        cls,
        action_id: str,
        acting_user: dict[str, Any],
    ) -> dict[str, Any]:
        """Authorized rollback / revocation of an active simulated rule."""
        tenant_id = acting_user.get("tenant_id")
        user_id = acting_user.get("user_id")
        user_role = acting_user.get("role")
        now_str = datetime.now(UTC).isoformat()

        if user_role not in ("SECURITY_RESPONDER", "TENANT_ADMIN", "PLATFORM_ADMIN"):
            raise ResponsePolicyError(f"Unauthorized: Role '{user_role}' cannot execute action rollbacks.")

        with get_db() as conn:
            action = conn.execute(
                "SELECT * FROM action_journal WHERE action_id = ? AND tenant_id = ?",
                (action_id, tenant_id),
            ).fetchone()
            if not action:
                raise ResponsePolicyError(f"Action '{action_id}' not found for tenant '{tenant_id}'.")

            rule = conn.execute(
                "SELECT * FROM simulated_firewall_rules WHERE action_id = ? AND tenant_id = ?",
                (action_id, tenant_id),
            ).fetchone()

            if rule:
                FirewallSimulator.revoke_rule(rule["rule_id"], tenant_id)

            conn.execute(
                "UPDATE action_journal SET status = 'ROLLED_BACK' WHERE action_id = ?",
                (action_id,),
            )

            conn.execute(
                """
                INSERT INTO audit_events (
                    audit_id, tenant_id, actor_id, event_action,
                    resource_type, resource_id, details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"aud_{uuid.uuid4().hex[:12]}",
                    tenant_id,
                    user_id,
                    "ACTION_ROLLED_BACK",
                    "ACTION",
                    action_id,
                    json.dumps({"action_id": action_id, "status": "ROLLED_BACK"}),
                    now_str,
                ),
            )

            updated = conn.execute("SELECT * FROM action_journal WHERE action_id = ?", (action_id,)).fetchone()
            return dict(updated)

    @classmethod
    def get_action(cls, action_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
        """Retrieve single action record by ID."""
        with get_db() as conn:
            query = "SELECT * FROM action_journal WHERE action_id = ?"
            params = [action_id]
            if tenant_id:
                query += " AND tenant_id = ?"
                params.append(tenant_id)
            row = conn.execute(query, tuple(params)).fetchone()
            return dict(row) if row else None

    @classmethod
    def list_actions(cls, tenant_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """List action journal entries scoped to tenant."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM action_journal WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
                (tenant_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]
