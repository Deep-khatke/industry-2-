"""Development, demonstration replay, and test harness API endpoints."""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..auth.dependencies import get_current_user, verify_tenant_boundary
from ..config import settings
from ..database import reset_db, seed_demo_data
from ..telemetry.ingest import TelemetryIngestionPipeline
from ..telemetry.replay import ReplayCoordinator

router = APIRouter(prefix="/v1/dev", tags=["Development & Demo"])


class StartReplayRequest(BaseModel):
    scenario: str = Field(default="suspicious", description="Scenario type: normal, suspicious, scanning, mixed")
    tenant_id: str = Field(default="rural-isp-alpha", description="Target ISP tenant identifier")


class IngestBatchRequest(BaseModel):
    tenant_id: str = Field(default="rural-isp-alpha", description="Target ISP tenant identifier")
    records: list[dict[str, Any]] = Field(default_factory=list, description="List of raw flow record dictionaries")


def verify_dev_mode() -> None:
    if not settings.is_development or not settings.allow_demo_endpoints:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Development endpoints are disabled outside DEVELOPMENT mode.",
        )


@router.post("/replay/start")
def start_replay(
    req: StartReplayRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Trigger a reproducible synthetic flow telemetry replay scenario for demonstration and testing.
    Scenarios:
    - 'normal': Benign traffic, no false alarms generated.
    - 'suspicious': Volumetric flood burst matching DDoS detection rules and high ML risk score.
    - 'scanning': SYN port scan probe sequence matching reconnaissance detection rules.
    - 'mixed': Combined normal traffic followed by suspicious bursts.
    """
    verify_dev_mode()
    verify_tenant_boundary(user, req.tenant_id)

    if req.scenario not in ("normal", "suspicious", "scanning", "mixed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported scenario '{req.scenario}'. Allowed: normal, suspicious, scanning, mixed",
        )

    result = ReplayCoordinator.run_scenario(scenario=req.scenario, tenant_id=req.tenant_id)
    return result


@router.get("/replay/status")
def get_replay_status(
    _user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve active status and history of the synthetic replay coordinator."""
    verify_dev_mode()
    return ReplayCoordinator.get_status()


@router.post("/reset")
def reset_demo_database(
    _user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Wipe and re-seed the development demonstration database to its clean initial state.
    Strictly prohibited in non-development environments.
    """
    verify_dev_mode()
    reset_db()
    seed_demo_data()
    return {
        "status": "RESET_SUCCESSFUL",
        "message": "Development database reset and re-seeded with demo tenants, users, and baseline configurations.",
    }


@router.post("/telemetry/ingest")
def ingest_real_flows(
    req: IngestBatchRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Ingest arbitrary real or custom flow telemetry records directly into the pipeline.
    Executes window aggregation, feature extraction, and ML scoring.
    """
    verify_dev_mode()
    verify_tenant_boundary(user, req.tenant_id)

    pipeline = TelemetryIngestionPipeline()
    now_str = datetime.now(UTC).isoformat()
    processed = []
    incidents_created = 0

    for r in req.records:
        rec = dict(r)
        rec.setdefault("tenant_id", req.tenant_id)
        rec.setdefault("event_id", f"flow_real_{uuid.uuid4().hex[:12]}")
        rec.setdefault("event_time", now_str)
        rec.setdefault("exporter_id", "exp-alpha-core1")
        res = pipeline.ingest_record(rec)
        if res.get("incident_created"):
            incidents_created += 1
        processed.append({
            "event_id": rec.get("event_id"),
            "status": res.get("status"),
            "is_threat": res.get("detection", {}).get("is_threat", False),
            "severity": res.get("detection", {}).get("severity", "LOW"),
            "attack_category": res.get("detection", {}).get("attack_category", "BENIGN"),
            "composite_risk": res.get("detection", {}).get("composite_risk", 0.0),
            "incident_created": res.get("incident_created", False),
        })

    return {
        "status": "INGESTION_COMPLETED",
        "tenant_id": req.tenant_id,
        "records_ingested": len(processed),
        "incidents_created": incidents_created,
        "results": processed,
    }
