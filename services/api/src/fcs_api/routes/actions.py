"""Manual Response Actions and Firewall Simulator API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..auth.dependencies import get_current_user, verify_tenant_boundary
from ..firewall.simulator import FirewallSimulator
from ..response.policy import ResponsePolicyEngine, ResponsePolicyError

router = APIRouter(prefix="/v1", tags=["Manual Response Actions"])


class ExecuteActionRequest(BaseModel):
    action_type: str = Field(..., description="Action type: TEMPORARY_BLOCK or RATE_LIMIT")
    target: str = Field(..., description="Target IPv4 or IPv6 address")
    duration_seconds: int = Field(default=900, ge=60, le=3600, description="Duration in seconds (bounded non-permanent)")
    idempotency_key: str = Field(..., min_length=8, description="Unique client idempotency token")
    scope: str = Field(default="EDGE_FIREWALL", description="Enforcement boundary")
    recommendation_id: str | None = Field(default=None, description="Optional linked recommendation ID")


@router.post("/incidents/{incident_id}/actions")
def approve_and_execute_action(
    incident_id: str,
    req: ExecuteActionRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Approve and execute a defensive response action in Manual Mode.
    Requires SECURITY_RESPONDER or TENANT_ADMIN role.
    Target must not be protected infrastructure.
    Executes in isolated software firewall simulator with verified read-back.
    """
    try:
        result = ResponsePolicyEngine.execute_manual_action(
            incident_id=incident_id,
            action_type=req.action_type,
            target=req.target,
            duration_seconds=req.duration_seconds,
            acting_user=user,
            idempotency_key=req.idempotency_key,
            scope=req.scope,
            recommendation_id=req.recommendation_id,
        )
        return result
    except ResponsePolicyError as e:
        err_msg = str(e)
        if "Unauthorized" in err_msg:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=err_msg) from e
        if "not found" in err_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg) from e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg) from e


@router.get("/actions")
def list_actions(
    tenant_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List response actions journal entries for authorized tenant."""
    target_tenant_id = tenant_id or user.get("tenant_id") or "rural-isp-alpha"
    verify_tenant_boundary(user, target_tenant_id)
    return ResponsePolicyEngine.list_actions(tenant_id=target_tenant_id, limit=limit)


@router.get("/actions/{action_id}")
def get_action(
    action_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve action record with tenant boundary enforcement."""
    action = ResponsePolicyEngine.get_action(action_id)
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action '{action_id}' not found.",
        )
    verify_tenant_boundary(user, action["tenant_id"])
    return action


@router.post("/actions/{action_id}/rollback")
def rollback_action(
    action_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Roll back an active defensive action rule.
    Requires SECURITY_RESPONDER or TENANT_ADMIN role.
    """
    try:
        return ResponsePolicyEngine.rollback_action(action_id=action_id, acting_user=user)
    except ResponsePolicyError as e:
        err_msg = str(e)
        if "Unauthorized" in err_msg:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=err_msg) from e
        if "not found" in err_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg) from e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg) from e


@router.get("/firewall/rules")
def list_active_firewall_rules(
    tenant_id: str | None = Query(default=None),
    include_expired: bool = Query(default=False),
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Inspect active rules in isolated software firewall simulator."""
    target_tenant_id = tenant_id or user.get("tenant_id") or "rural-isp-alpha"
    verify_tenant_boundary(user, target_tenant_id)
    return FirewallSimulator.list_active_rules(tenant_id=target_tenant_id, include_expired=include_expired)
