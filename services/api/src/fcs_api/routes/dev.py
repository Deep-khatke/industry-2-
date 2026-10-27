"""Development, demonstration replay, and test harness API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..auth.dependencies import get_current_user, verify_tenant_boundary
from ..config import settings
from ..database import reset_db, seed_demo_data
from ..telemetry.replay import ReplayCoordinator

router = APIRouter(prefix="/v1/dev", tags=["Development & Demo"])


class StartReplayRequest(BaseModel):
    scenario: str = Field(default="suspicious", description="Scenario type: normal, suspicious, scanning, mixed")
    tenant_id: str = Field(default="rural-isp-alpha", description="Target ISP tenant identifier")


def verify_dev_mode() -> None:
    if settings.environment != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Development endpoints are disabled in production configurations.",
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
