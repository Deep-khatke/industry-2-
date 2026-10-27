"""Defensive recommendation generator based on detected threats and evidence."""

import uuid
from datetime import UTC, datetime
from typing import Any

from ..database import get_db


class RecommendationGenerator:
    """Generates structured defensive recommendations for detected security incidents."""

    @staticmethod
    def generate_recommendation(incident: dict[str, Any]) -> dict[str, Any]:
        """
        Produce actionable, bounded defensive recommendation for an incident.
        Stores recommendation in database with status 'PROPOSED'.
        """
        rec_id = f"rec_{uuid.uuid4().hex[:12]}"
        incident_id = incident["incident_id"]
        tenant_id = incident["tenant_id"]
        attack_category = incident.get("attack_category", "Unknown")
        severity = incident.get("severity", "MEDIUM")
        target_ip = incident.get("target_ip") or "198.51.100.42"
        now = datetime.now(UTC).isoformat()

        if attack_category in ("DDoS", "Flood"):
            action_type = "TEMPORARY_BLOCK"
            duration = 900  # 15 minutes
            reason = f"Block source IP {target_ip} at edge firewall to halt active volumetric flood."
            risk_level = "HIGH"
        elif attack_category in ("PortScan", "Reconnaissance"):
            action_type = "RATE_LIMIT"
            duration = 1800  # 30 minutes
            reason = f"Apply rate-limiting policy (100 pps) to throttle reconnaissance scanning from {target_ip}."
            risk_level = "MEDIUM"
        elif attack_category in ("DoS", "Slowloris"):
            action_type = "RATE_LIMIT"
            duration = 600  # 10 minutes
            reason = f"Throttle keepalive connection rate for {target_ip} to protect session pool."
            risk_level = "LOW"
        else:
            action_type = "TEMPORARY_BLOCK" if severity in ("HIGH", "CRITICAL") else "RATE_LIMIT"
            duration = 300  # 5 minutes
            reason = f"Defensive mitigation for {attack_category} targeting {target_ip}."
            risk_level = severity

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO recommendations (
                    recommendation_id, incident_id, tenant_id, action_type,
                    target, scope, recommended_duration_seconds, reason,
                    risk_level, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rec_id,
                    incident_id,
                    tenant_id,
                    action_type,
                    target_ip,
                    "EDGE_FIREWALL",
                    duration,
                    reason,
                    risk_level,
                    "PROPOSED",
                    now,
                ),
            )

        return {
            "recommendation_id": rec_id,
            "incident_id": incident_id,
            "tenant_id": tenant_id,
            "action_type": action_type,
            "target": target_ip,
            "scope": "EDGE_FIREWALL",
            "recommended_duration_seconds": duration,
            "reason": reason,
            "risk_level": risk_level,
            "status": "PROPOSED",
            "created_at": now,
        }
