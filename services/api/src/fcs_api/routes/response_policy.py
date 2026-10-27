"""Response Policy API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends

from ..auth.dependencies import get_current_user
from ..config import settings

router = APIRouter(prefix="/v1", tags=["Response Policy"])


@router.get("/response-policy")
def get_response_policy(
    _user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Retrieve active defensive response policy configuration.
    Phase 4 strictly enforces MANUAL Mode with human administrator approval.
    """
    return {
        "response_mode": settings.response_mode,  # "MANUAL"
        "auto_response_enabled": False,
        "auto_response_status": "AUTO response is unavailable until the dedicated safety qualification phase.",
        "allowed_manual_actions": ["TEMPORARY_BLOCK", "RATE_LIMIT"],
        "min_duration_seconds": settings.min_action_duration_seconds,
        "max_duration_seconds": settings.max_action_duration_seconds,
        "protected_ip_ranges": settings.protected_ip_ranges,
        "execution_boundary": "ISOLATED_FIREWALL_SIMULATOR",
        "requires_roles": ["SECURITY_RESPONDER", "TENANT_ADMIN"],
        "simulation_disclaimer": "Simulated defensive action — no real network device modified.",
        "idempotency_enforced": True,
        "rollback_supported": True,
    }
