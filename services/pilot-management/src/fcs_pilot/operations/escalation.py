"""Incident lifecycle state management and operational escalation matrix."""

import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger("fcs_pilot.escalation")


class IncidentLifecycleState(StrEnum):
    """Permitted states in the SOC incident management lifecycle."""
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    ESCALATED = "ESCALATED"
    ACTION_RECOMMENDED = "ACTION_RECOMMENDED"
    ACTION_PENDING_APPROVAL = "ACTION_PENDING_APPROVAL"
    SIMULATED_ACTION_VERIFIED = "SIMULATED_ACTION_VERIFIED"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    CLOSED = "CLOSED"


class EscalationLevel(StrEnum):
    """Severity and operational escalation tiers."""
    INFORMATIONAL = "INFORMATIONAL"
    REPEATED_SUSPICIOUS = "REPEATED_SUSPICIOUS"
    HIGH_SEVERITY = "HIGH_SEVERITY"
    CRITICAL_ATTACK = "CRITICAL_ATTACK"
    TELEMETRY_COVERAGE_LOSS = "TELEMETRY_COVERAGE_LOSS"
    MODEL_FAILURE = "MODEL_FAILURE"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class EscalationMatrixEntry(BaseModel):
    """Escalation routing rule based on condition."""
    escalation_level: EscalationLevel
    assigned_tier: str  # "Tier-1 SOC", "Tier-2 Responder", "Lead Network Engineer", "CISO / Admin"
    target_sla_minutes: int
    notification_channel: str
    action_authority: str
    pause_telemetry_recommended: bool = False


class IncidentEscalationManager:
    """Governs incident state transitions and escalation matrix routing."""

    ESCALATION_MATRIX: dict[EscalationLevel, EscalationMatrixEntry] = {
        EscalationLevel.INFORMATIONAL: EscalationMatrixEntry(
            escalation_level=EscalationLevel.INFORMATIONAL,
            assigned_tier="Tier-1 SOC Analyst",
            target_sla_minutes=60,
            notification_channel="SOC Incident Queue",
            action_authority="None (Observational only)",
        ),
        EscalationLevel.REPEATED_SUSPICIOUS: EscalationMatrixEntry(
            escalation_level=EscalationLevel.REPEATED_SUSPICIOUS,
            assigned_tier="Tier-1 SOC Analyst",
            target_sla_minutes=15,
            notification_channel="SOC Alert Banner",
            action_authority="Recommend Manual Action",
        ),
        EscalationLevel.HIGH_SEVERITY: EscalationMatrixEntry(
            escalation_level=EscalationLevel.HIGH_SEVERITY,
            assigned_tier="Tier-2 Security Responder",
            target_sla_minutes=5,
            notification_channel="High-Priority SOC Dispatch",
            action_authority="Approve Simulated Action",
        ),
        EscalationLevel.CRITICAL_ATTACK: EscalationMatrixEntry(
            escalation_level=EscalationLevel.CRITICAL_ATTACK,
            assigned_tier="Lead Network Engineer & Tenant Admin",
            target_sla_minutes=2,
            notification_channel="Emergency Bridge",
            action_authority="Executive Response Approval",
        ),
        EscalationLevel.TELEMETRY_COVERAGE_LOSS: EscalationMatrixEntry(
            escalation_level=EscalationLevel.TELEMETRY_COVERAGE_LOSS,
            assigned_tier="ISP Network Operations Center (NOC)",
            target_sla_minutes=10,
            notification_channel="NOC Incident Ticket",
            action_authority="Exporter Check / Router Interface Verification",
        ),
        EscalationLevel.MODEL_FAILURE: EscalationMatrixEntry(
            escalation_level=EscalationLevel.MODEL_FAILURE,
            assigned_tier="Applied ML / Platform Operations",
            target_sla_minutes=5,
            notification_channel="Platform Alert",
            action_authority="Execute Model Rollback to Previous Version",
        ),
        EscalationLevel.EMERGENCY_STOP: EscalationMatrixEntry(
            escalation_level=EscalationLevel.EMERGENCY_STOP,
            assigned_tier="Platform Admin / All Responders",
            target_sla_minutes=1,
            notification_channel="Emergency Broadcast",
            action_authority="Instantaneous Rule Rollback (< 10s)",
            pause_telemetry_recommended=True,
        ),
    }

    def __init__(self) -> None:
        self._incident_states: dict[str, IncidentLifecycleState] = {}
        self._emergency_stop_active = False

    def get_state(self, incident_id: str) -> IncidentLifecycleState:
        return self._incident_states.get(incident_id, IncidentLifecycleState.NEW)

    def transition_state(
        self,
        incident_id: str,
        new_state: IncidentLifecycleState,
        actor_id: str,
    ) -> IncidentLifecycleState:
        """Update incident state with audit log."""
        self._incident_states[incident_id] = new_state
        logger.info(f"Incident {incident_id} moved to {new_state} by {actor_id}.")
        return new_state

    def get_escalation_route(self, level: EscalationLevel) -> EscalationMatrixEntry:
        return self.ESCALATION_MATRIX[level]

    def trigger_emergency_pause(self, actor_id: str, reason: str) -> dict[str, Any]:
        """
        Instantaneous Emergency Pause / Kill-Switch.
        Rolls back all active rules and pauses collection.
        """
        self._emergency_stop_active = True
        logger.critical(f"EMERGENCY KILL-SWITCH TRIGGERED by {actor_id}: {reason}")
        return {
            "emergency_pause_active": True,
            "timestamp": datetime.now(UTC).isoformat(),
            "triggered_by": actor_id,
            "reason": reason,
            "rollback_all_simulated_rules": True,
            "status": "ALL_RULES_PURGED",
        }

    def resume_from_emergency_pause(self, actor_id: str) -> dict[str, Any]:
        self._emergency_stop_active = False
        logger.info(f"Emergency pause cleared by {actor_id}.")
        return {"emergency_pause_active": False, "status": "RESUMED"}
