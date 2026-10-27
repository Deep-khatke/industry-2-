"""Durable incident management, deduplication, and lifecycle state engine."""

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from ..config import settings
from ..database import get_db
from ..recommendations.generator import RecommendationGenerator

VALID_TRANSITIONS: dict[str, set[str]] = {
    "NEW": {"ACKNOWLEDGED", "INVESTIGATING", "ACTION_PENDING", "MITIGATED", "FALSE_POSITIVE", "RESOLVED"},
    "ACKNOWLEDGED": {"INVESTIGATING", "ACTION_PENDING", "MITIGATED", "RESOLVED", "FALSE_POSITIVE"},
    "INVESTIGATING": {"ACTION_PENDING", "MITIGATED", "RESOLVED", "FALSE_POSITIVE"},
    "ACTION_PENDING": {"MITIGATED", "RESOLVED", "INVESTIGATING"},
    "MITIGATED": {"RESOLVED", "CLOSED"},
    "RESOLVED": {"CLOSED", "INVESTIGATING"},
    "FALSE_POSITIVE": {"CLOSED"},
    "CLOSED": set(),  # Terminal state
}


class IncidentManager:
    """Manages persistent incidents, deduplication windows, history, and state transitions."""

    @classmethod
    def process_detection(
        cls,
        detection_result: dict[str, Any],
        flow_event: dict[str, Any] | None = None,
        window_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Evaluate if detection qualifies as an incident.
        Deduplicates against active incidents within the configured grouping window.
        """
        if not detection_result.get("is_threat", False):
            return None

        tenant_id = detection_result["tenant_id"]
        attack_category = detection_result["attack_category"]
        severity = detection_result["severity"]
        risk_score = detection_result["risk_score"]

        # Determine target IP and port based on attack category
        target_ip = "198.51.100.42"
        target_port = 80
        if flow_event:
            if attack_category in ("DDoS", "Volumetric Flood"):
                target_ip = flow_event.get("dst_ip") or "198.51.100.88"
                target_port = int(flow_event.get("dst_port") or 443)
            else:
                target_ip = flow_event.get("src_prefix_masked") or flow_event.get("src_ip") or "198.51.100.42"
                target_port = int(flow_event.get("dst_port") or 80)
        elif window_data and "feature_vector" in window_data:
            target_port = int(window_data["feature_vector"].get("L4_DST_PORT", 80))

        grouping_key = f"{tenant_id}:{target_ip}:{attack_category}"
        now_dt = datetime.now(UTC)
        cutoff_dt = now_dt - timedelta(seconds=settings.incident_grouping_window_seconds)
        now_str = now_dt.isoformat()

        with get_db() as conn:
            # Check for recent active incident with identical grouping key
            existing = conn.execute(
                """
                SELECT * FROM incidents
                WHERE tenant_id = ? AND grouping_key = ? AND status NOT IN ('RESOLVED', 'CLOSED', 'FALSE_POSITIVE')
                  AND updated_at >= ?
                ORDER BY updated_at DESC LIMIT 1
                """,
                (tenant_id, grouping_key, cutoff_dt.isoformat()),
            ).fetchone()

            if existing:
                incident_id = existing["incident_id"]
                updated_risk = max(existing["risk_score"], risk_score)
                conn.execute(
                    """
                    UPDATE incidents
                    SET risk_score = ?, updated_at = ?
                    WHERE incident_id = ?
                    """,
                    (updated_risk, now_str, incident_id),
                )
                return dict(existing)

            # Create new incident
            incident_id = f"inc_{uuid.uuid4().hex[:12]}"
            title = f"{severity} {attack_category} Detection on {target_ip}:{target_port}"
            evidence = {
                "detection_score_id": detection_result.get("score_id"),
                "window_id": window_data.get("window_id") if window_data else None,
                "risk_score": risk_score,
                "ml_inference": detection_result.get("ml_inference"),
                "multi_model_evidence": detection_result.get("multi_model_evidence"),
                "sample_flow": flow_event,
            }

            conn.execute(
                """
                INSERT INTO incidents (
                    incident_id, tenant_id, grouping_key, title, attack_category,
                    severity, status, risk_score, target_ip, target_port,
                    evidence_json, model_version, rule_matches_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    incident_id,
                    tenant_id,
                    grouping_key,
                    title,
                    attack_category,
                    severity,
                    "NEW",
                    risk_score,
                    target_ip,
                    target_port,
                    json.dumps(evidence, default=str),
                    "1.2.0",
                    json.dumps(detection_result.get("rule_matches", []), default=str),
                    now_str,
                    now_str,
                ),
            )

            # Record initial history entry
            conn.execute(
                """
                INSERT INTO incident_history (
                    history_id, incident_id, tenant_id, actor_id,
                    previous_status, new_status, change_notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"hist_{uuid.uuid4().hex[:12]}",
                    incident_id,
                    tenant_id,
                    "system:detection_engine",
                    "NONE",
                    "NEW",
                    "Initial detection incident created.",
                    now_str,
                ),
            )

            # Transactional notification outbox entry
            conn.execute(
                """
                INSERT INTO notification_outbox (
                    outbox_id, tenant_id, event_type, payload_json, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    f"out_{uuid.uuid4().hex[:12]}",
                    tenant_id,
                    "INCIDENT_CREATED",
                    json.dumps({"incident_id": incident_id, "title": title, "severity": severity}),
                    "PENDING",
                    now_str,
                ),
            )

        incident_record = {
            "incident_id": incident_id,
            "tenant_id": tenant_id,
            "title": title,
            "attack_category": attack_category,
            "severity": severity,
            "status": "NEW",
            "risk_score": risk_score,
            "target_ip": target_ip,
            "target_port": target_port,
            "evidence": evidence,
            "created_at": now_str,
        }

        # Generate defensive recommendation
        RecommendationGenerator.generate_recommendation(incident_record)
        return incident_record

    @classmethod
    def update_incident_status(
        cls,
        incident_id: str,
        new_status: str,
        actor_id: str,
        notes: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Update incident lifecycle state with transition validation."""
        now_str = datetime.now(UTC).isoformat()
        with get_db() as conn:
            query = "SELECT * FROM incidents WHERE incident_id = ?"
            params = [incident_id]
            if tenant_id:
                query += " AND tenant_id = ?"
                params.append(tenant_id)

            row = conn.execute(query, tuple(params)).fetchone()
            if not row:
                raise ValueError(f"Incident '{incident_id}' not found.")

            current_status = row["status"]
            if current_status == new_status:
                return dict(row)

            allowed = VALID_TRANSITIONS.get(current_status, set())
            if new_status not in allowed:
                raise ValueError(
                    f"Invalid state transition: Cannot transition from '{current_status}' to '{new_status}'. Allowed: {sorted(allowed)}"
                )

            # Update incident
            ack_time = now_str if new_status == "ACKNOWLEDGED" else row["acknowledged_at"]
            res_time = now_str if new_status in ("RESOLVED", "CLOSED", "FALSE_POSITIVE") else row["resolved_at"]

            conn.execute(
                """
                UPDATE incidents
                SET status = ?, acknowledged_at = ?, resolved_at = ?, updated_at = ?
                WHERE incident_id = ?
                """,
                (new_status, ack_time, res_time, now_str, incident_id),
            )

            # Record history
            conn.execute(
                """
                INSERT INTO incident_history (
                    history_id, incident_id, tenant_id, actor_id,
                    previous_status, new_status, change_notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"hist_{uuid.uuid4().hex[:12]}",
                    incident_id,
                    row["tenant_id"],
                    actor_id,
                    current_status,
                    new_status,
                    notes or f"Status changed to {new_status}",
                    now_str,
                ),
            )

            updated = conn.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)).fetchone()
            return dict(updated)

    @classmethod
    def list_incidents(
        cls,
        tenant_id: str,
        status: str | None = None,
        severity: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query incidents with filtering and pagination scoped strictly to tenant_id."""
        with get_db() as conn:
            query = "SELECT * FROM incidents WHERE tenant_id = ?"
            params: list[Any] = [tenant_id]

            if status:
                query += " AND status = ?"
                params.append(status)
            if severity:
                query += " AND severity = ?"
                params.append(severity)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = conn.execute(query, tuple(params)).fetchall()
            return [dict(r) for r in rows]

    @classmethod
    def get_incident(cls, incident_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
        """Retrieve single incident by ID scoped to tenant."""
        with get_db() as conn:
            query = "SELECT * FROM incidents WHERE incident_id = ?"
            params = [incident_id]
            if tenant_id:
                query += " AND tenant_id = ?"
                params.append(tenant_id)
            row = conn.execute(query, tuple(params)).fetchone()
            return dict(row) if row else None

    @classmethod
    def get_history(cls, incident_id: str) -> list[dict[str, Any]]:
        """Retrieve full audit history timeline for an incident."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM incident_history WHERE incident_id = ? ORDER BY created_at ASC",
                (incident_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    @classmethod
    def get_recommendations(cls, incident_id: str) -> list[dict[str, Any]]:
        """Retrieve recommendations for an incident."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM recommendations WHERE incident_id = ? ORDER BY created_at DESC",
                (incident_id,),
            ).fetchall()
            return [dict(r) for r in rows]
