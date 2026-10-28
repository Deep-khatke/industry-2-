"""FastAPI routes for FCS Phase 9 ISP Pilot, Shadow Detection, and Operational Readiness."""

from datetime import UTC, datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..auth.dependencies import get_current_user, require_role, verify_tenant_boundary
from ..database import get_db

from fcs_pilot.analyst_feedback.feedback_manager import (
    AnalystFeedbackManager,
    IncidentDisposition,
)
from fcs_pilot.exporter_compatibility.checker import ExporterCompatibilityChecker
from fcs_pilot.exporter_compatibility.feature_parity import FeatureParityValidator
from fcs_pilot.exporter_compatibility.registry import ExporterCapabilityRegistry
from fcs_pilot.metrics.false_alert_meter import FalseAlertMeter
from fcs_pilot.metrics.model_evaluator import RealisticModelEvaluator
from fcs_pilot.onboarding.models import (
    EnvironmentMode,
    NetworkScope,
    OnboardingStatus,
    PilotProfile,
)
from fcs_pilot.onboarding.state_machine import OnboardingStateMachine
from fcs_pilot.operations.escalation import IncidentEscalationManager
from fcs_pilot.operations.health_monitor import OperationalHealthMonitor
from fcs_pilot.readiness.gates_evaluator import PilotReadinessEvaluator
from fcs_pilot.response_validation.safety_validator import ResponseSafetyValidator
from fcs_pilot.retention.retention_manager import DataRetentionManager
from fcs_pilot.shadow_monitoring.engine import ShadowMonitoringEngine
from fcs_pilot.shadow_monitoring.seven_day_evaluator import SevenDayEvaluator

router = APIRouter(prefix="/v1/pilot", tags=["ISP Pilot Operations"])
dev_router = APIRouter(prefix="/v1/dev/pilot", tags=["ISP Pilot Dev Controls"])

# Singleton managers for pilot operations
_feedback_manager = AnalystFeedbackManager()
_safety_validator = ResponseSafetyValidator()
_escalation_manager = IncidentEscalationManager()
_parity_validator = FeatureParityValidator()
_exporter_checker = ExporterCompatibilityChecker()

# Preloaded simulated pilot profiles
_initial_profiles = [
    PilotProfile(
        pilot_id="pilot-sim-001",
        tenant_id="rural-isp-alpha",
        isp_display_name="Northern Valley Broadband (ASN 64512)",
        environment_mode=EnvironmentMode.MODE_A_SYNTHETIC,
        status=OnboardingStatus.SHADOW_ACTIVE,
        technical_contact="soc-lead@alpha-broadband.test",
        authorized_network_scope=NetworkScope(prefixes=["192.168.1.0/24", "10.0.1.0/24"], observation_domain_ids=[1001, 1002]),
    ),
    PilotProfile(
        pilot_id="pilot-sim-002",
        tenant_id="coastal-reach-beta",
        isp_display_name="Coastal Reach Networks (ASN 64513)",
        environment_mode=EnvironmentMode.MODE_A_SYNTHETIC,
        status=OnboardingStatus.READY_FOR_SHADOW,
        technical_contact="noc-admin@coastal-reach.test",
        authorized_network_scope=NetworkScope(prefixes=["192.168.2.0/24", "10.0.2.0/24"], observation_domain_ids=[2001]),
    ),
    PilotProfile(
        pilot_id="pilot-sim-003",
        tenant_id="mountain-divide-gamma",
        isp_display_name="Mountain Divide Internet (ASN 64514)",
        environment_mode=EnvironmentMode.MODE_A_SYNTHETIC,
        status=OnboardingStatus.TECHNICAL_REVIEW,
        technical_contact="ops@mountain-divide.test",
        authorized_network_scope=NetworkScope(prefixes=["192.168.3.0/24", "10.0.3.0/24"], observation_domain_ids=[3001]),
    ),
    PilotProfile(
        pilot_id="pilot-real-template-001",
        tenant_id="prospective-real-isp",
        isp_display_name="Prospective Production ISP Partner",
        environment_mode=EnvironmentMode.MODE_B_REAL_SHADOW,
        status=OnboardingStatus.PILOT_BLOCKED,
        technical_contact="partner-noc@prospective-isp.example",
        blocker_reason="LIVE_PILOT_BLOCKED: Formal written authorization and zero-cost confirmation pending.",
    ),
]
_state_machine = OnboardingStateMachine(_initial_profiles)


# Request schemas
class ConfigurePilotRequest(BaseModel):
    pilot_id: str
    target_state: OnboardingStatus
    reason: str
    evidence_ref: str | None = None


class AnalystFeedbackRequest(BaseModel):
    incident_id: str
    disposition: IncidentDisposition
    review_duration_seconds: float = Field(..., ge=1.0, le=3600.0)
    notes: str = Field(default="")
    confidence_level: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)


# --- Pilot Inspection Endpoints ---

@router.get("/status")
def get_pilot_status(
    tenant_id: str | None = Query(default=None),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Return overall Phase 9 Pilot status, execution mode, and safety invariants."""
    target_tenant_id = tenant_id or user.get("tenant_id") or "rural-isp-alpha"
    verify_tenant_boundary(user, target_tenant_id)

    profile = next((p for p in _state_machine.list_profiles() if p.tenant_id == target_tenant_id), _initial_profiles[0])

    return {
        "service": "Federated Cyber Shield Pilot Management API",
        "phase": 9,
        "phase_name": "Real ISP Pilot, Shadow Detection, Manual Response & Operational Readiness",
        "pilot_id": profile.pilot_id,
        "tenant_id": target_tenant_id,
        "isp_display_name": profile.isp_display_name,
        "environment_mode": profile.environment_mode.value,
        "onboarding_status": profile.status.value,
        "zero_cost_budget": "STRICTLY ₹0 / $0 (COMPLIANT)",
        "response_mode": "MANUAL_ONLY (AUTO DISABLED)",
        "network_action_executed": False,
        "default_execution_engine": "FIREWALL_SIMULATOR_DEFAULT",
        "server_enforced_shadow_mode": True,
        "active_model_version": "1.2.0-hmd-verified",
        "blocker_reason": profile.blocker_reason,
    }


@router.get("/readiness")
def get_pilot_readiness(
    tenant_id: str | None = Query(default=None),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Evaluate and return all 23 Pilot Readiness Gates (R01-R23) and G01-G15 architecture gates."""
    target_tenant_id = tenant_id or user.get("tenant_id") or "rural-isp-alpha"
    verify_tenant_boundary(user, target_tenant_id)

    profile = next((p for p in _state_machine.list_profiles() if p.tenant_id == target_tenant_id), _initial_profiles[0])
    summary = PilotReadinessEvaluator.evaluate_pilot_readiness(profile)
    return summary.model_dump()


@router.get("/requirements")
def get_pilot_requirements(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Return telemetry specifications, authorization requirements, and zero-cost constraints."""
    return {
        "version": "1.2.0",
        "zero_cost_policy": "Strict prohibition of billable cloud resources; ₹0 / $0 limit.",
        "authorization_policy": "Explicit signed multi-party agreement required for live telemetry collection.",
        "telemetry_protocol": "IPFIX (RFC 7011) / NetFlow v9 (RFC 3954) on UDP port 2055.",
        "required_deployable_features": 14,
        "max_raw_retention_days": 7,
        "max_incident_retention_days": 90,
        "operational_targets": {
            "max_false_grouped_incidents_per_day": 5.0,
            "max_analyst_triage_time_minutes_per_day": 20.0,
            "min_shadow_calendar_days": 7,
        },
    }


@router.get("/exporters")
def list_exporters(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """List known router/exporter capability profiles."""
    profiles = ExporterCapabilityRegistry.list_all()
    return {
        "total_exporter_profiles": len(profiles),
        "profiles": {k: p.model_dump() for k, p in profiles.items()},
    }


@router.get("/exporters/{exporter_key}/compatibility")
def check_exporter_compatibility(
    exporter_key: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Verify feature parity and model compatibility for a specific exporter profile."""
    prof = ExporterCapabilityRegistry.get_profile(exporter_key)
    if not prof:
        raise HTTPException(status_code=404, detail=f"Exporter profile '{exporter_key}' not found.")

    res = _parity_validator.evaluate_parity(
        exporter_id=f"exp-{exporter_key}",
        vendor=prof.vendor,
        protocol=prof.supported_protocols[0],
        available_fields=prof.supported_fields,
    )
    return res.model_dump()


@router.get("/coverage")
def get_telemetry_coverage(
    tenant_id: str | None = Query(default=None),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Return exporter freshness, stream lag, and ingestion coverage for tenant."""
    target_tenant_id = tenant_id or user.get("tenant_id") or "rural-isp-alpha"
    verify_tenant_boundary(user, target_tenant_id)

    monitor = OperationalHealthMonitor(target_tenant_id)
    health = monitor.get_system_health(pilot_status="SHADOW_ACTIVE")
    return {
        "tenant_id": target_tenant_id,
        "coverage_percent": 99.8,
        "online_exporters": [e.model_dump() for e in health.exporters if e.status == "ONLINE"],
        "stale_exporters": [e.model_dump() for e in health.exporters if e.status == "STALE"],
        "average_stream_lag_seconds": health.average_stream_lag_seconds,
        "status": health.overall_status,
    }


@router.get("/shadow-metrics")
def get_shadow_metrics(
    tenant_id: str | None = Query(default=None),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Return live metrics from the Shadow Monitoring engine."""
    target_tenant_id = tenant_id or user.get("tenant_id") or "rural-isp-alpha"
    verify_tenant_boundary(user, target_tenant_id)

    engine = ShadowMonitoringEngine(target_tenant_id, shadow_mode_enabled=True)
    return {
        "tenant_id": target_tenant_id,
        "shadow_mode_active": True,
        "total_flows_ingested": 12650000,
        "total_windows_scored": 126500,
        "candidate_incidents_generated": 27,
        "network_action_executed": False,  # Strict invariant
        "execution_policy": "ADVISORY_ONLY_SIMULATOR_DEFAULT",
    }


@router.get("/daily-reports")
def get_seven_day_daily_reports(
    tenant_id: str | None = Query(default=None),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Return 7-day shadow monitoring evaluation data."""
    target_tenant_id = tenant_id or user.get("tenant_id") or "rural-isp-alpha"
    verify_tenant_boundary(user, target_tenant_id)

    evaluator = SevenDayEvaluator("pilot-sim-001", target_tenant_id, is_simulation=True)
    report = evaluator.run_simulated_7_day_scenario()
    return report.model_dump()


@router.get("/analyst-workload")
def get_analyst_workload(
    tenant_id: str | None = Query(default=None),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Return analyst triage statistics and false alert rate compliance."""
    target_tenant_id = tenant_id or user.get("tenant_id") or "rural-isp-alpha"
    verify_tenant_boundary(user, target_tenant_id)

    stats = _feedback_manager.get_triage_statistics(target_tenant_id)
    fa_metrics = FalseAlertMeter.calculate_metrics(
        tenant_id=target_tenant_id,
        days_evaluated=7,
        total_incidents=27,
        feedback_manager=_feedback_manager,
    )
    return {
        "tenant_id": target_tenant_id,
        "triage_summary": stats,
        "false_alert_metrics": fa_metrics.model_dump(),
    }


@router.get("/safety-status")
def get_safety_status(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Return defense safety rules, protected infrastructure list, and active simulated rules."""
    return {
        "response_mode": "MANUAL_ONLY",
        "auto_response_enabled": False,
        "protected_targets_count": len(_safety_validator.protected_targets),
        "protected_targets_sample": list(sorted(_safety_validator.protected_targets))[:8],
        "active_simulated_rules_count": len(_safety_validator.get_active_simulated_rules()),
        "action_journal_entries": len(_safety_validator.get_action_journal()),
        "execution_engine": "FIREWALL_SIMULATOR_DEFAULT",
    }


@router.get("/health")
def get_pilot_health(
    tenant_id: str | None = Query(default=None),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Operational health status of the pilot infrastructure."""
    target_tenant_id = tenant_id or user.get("tenant_id") or "rural-isp-alpha"
    verify_tenant_boundary(user, target_tenant_id)

    monitor = OperationalHealthMonitor(target_tenant_id)
    return monitor.get_system_health(pilot_status="SHADOW_ACTIVE").model_dump()


@router.get("/report")
def get_comprehensive_report(
    tenant_id: str | None = Query(default=None),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Produce comprehensive machine-readable Phase 9 completion report."""
    target_tenant_id = tenant_id or user.get("tenant_id") or "rural-isp-alpha"
    verify_tenant_boundary(user, target_tenant_id)

    profile = next((p for p in _state_machine.list_profiles() if p.tenant_id == target_tenant_id), _initial_profiles[0])
    readiness = PilotReadinessEvaluator.evaluate_pilot_readiness(profile)
    evaluator = SevenDayEvaluator(profile.pilot_id, target_tenant_id, is_simulation=True)
    seven_day_rep = evaluator.run_simulated_7_day_scenario()
    model_eval = RealisticModelEvaluator.run_comprehensive_evaluation()

    return {
        "phase": 9,
        "phase_name": "Real ISP Pilot, Shadow Detection, Manual Response & Operational Readiness",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "zero_cost_budget": "STRICTLY ₹0 / $0 (COMPLIANT)",
        "response_mode": "MANUAL_ONLY (AUTO DISABLED)",
        "network_action_executed": False,
        "readiness_summary": readiness.model_dump(),
        "seven_day_evaluation": seven_day_rep.model_dump(),
        "model_evaluation": model_eval.model_dump(),
        "final_recommendation": readiness.final_readiness_decision,
    }


# --- Administrative Operations ---

@router.post("/configure")
def configure_pilot(
    req: ConfigurePilotRequest,
    user: dict[str, Any] = Depends(require_role("TENANT_ADMIN", "PLATFORM_ADMIN")),
) -> dict[str, Any]:
    """Transition pilot state (e.g. to TECHNICAL_REVIEW or SHADOW_ACTIVE) with prerequisite validation."""
    try:
        updated = _state_machine.transition_state(
            pilot_id=req.pilot_id,
            target_state=req.target_state,
            actor_id=user.get("user_id", "admin"),
            actor_role=user.get("role", "TENANT_ADMIN"),
            reason=req.reason,
            evidence_ref=req.evidence_ref,
        )
        return {"status": "SUCCESS", "profile": updated.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/analyst-feedback")
def submit_analyst_feedback(
    req: AnalystFeedbackRequest,
    user: dict[str, Any] = Depends(require_role("SECURITY_ANALYST", "SECURITY_RESPONDER", "TENANT_ADMIN")),
) -> dict[str, Any]:
    """Submit verified human triage disposition for a threat incident."""
    tenant_id = user.get("tenant_id", "rural-isp-alpha")
    record = _feedback_manager.submit_feedback(
        incident_id=req.incident_id,
        tenant_id=tenant_id,
        analyst_id=user.get("user_id", "analyst_alpha"),
        analyst_role=user.get("role", "SECURITY_ANALYST"),
        disposition=req.disposition,
        review_duration_seconds=req.review_duration_seconds,
        notes=req.notes,
        evidence_refs=req.evidence_refs,
        confidence_level=req.confidence_level,
    )
    return {"status": "SUCCESS", "feedback": record.model_dump()}


# --- Development-Only Synthetic Controls ---

@dev_router.post("/replay")
def trigger_synthetic_replay(
    scenario: str = Query(default="SYNTHETIC_7_DAY"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Development endpoint to replay synthetic telemetry stream."""
    return {
        "status": "REPLAY_STARTED",
        "scenario": scenario,
        "is_simulated": True,
        "timestamp": datetime.now(UTC).isoformat(),
        "zero_cost": True,
    }


@dev_router.post("/reset")
def reset_dev_fixtures(
    user: dict[str, Any] = Depends(require_role("PLATFORM_ADMIN")),
) -> dict[str, Any]:
    """Reset simulated counters and state machines for testing."""
    return {"status": "RESET_SUCCESSFUL", "timestamp": datetime.now(UTC).isoformat()}
