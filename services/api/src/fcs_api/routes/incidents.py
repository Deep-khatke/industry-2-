"""Incident Management API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..auth.dependencies import get_current_user, verify_tenant_boundary
from ..database import get_db
from ..incidents.manager import IncidentManager

router = APIRouter(prefix="/v1/incidents", tags=["Incidents"])


class UpdateIncidentStatusRequest(BaseModel):
    status: str = Field(..., description="Target incident status (e.g. ACKNOWLEDGED, INVESTIGATING, MITIGATED, RESOLVED, FALSE_POSITIVE, CLOSED)")
    notes: str | None = Field(default=None, description="Operational notes or disposition reason")


@router.get("")
def list_incidents(
    tenant_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """List persistent incidents scoped strictly to authorized tenant."""
    target_tenant_id = tenant_id or user.get("tenant_id") or "rural-isp-alpha"
    verify_tenant_boundary(user, target_tenant_id)

    incidents = IncidentManager.list_incidents(
        tenant_id=target_tenant_id,
        status=status_filter,
        severity=severity,
        limit=limit,
        offset=offset,
    )

    with get_db() as conn:
        count_query = "SELECT COUNT(*) as total FROM incidents WHERE tenant_id = ?"
        count_params: list[Any] = [target_tenant_id]
        if status_filter:
            count_query += " AND status = ?"
            count_params.append(status_filter)
        if severity:
            count_query += " AND severity = ?"
            count_params.append(severity)
        total = conn.execute(count_query, tuple(count_params)).fetchone()["total"]

    return {
        "tenant_id": target_tenant_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "incidents": incidents,
    }


@router.get("/{incident_id}")
def get_incident(
    incident_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve detailed incident record with tenant isolation enforcement."""
    user_tenant = user.get("tenant_id")
    incident = IncidentManager.get_incident(incident_id, tenant_id=user_tenant)
    if not incident:
        # Check if it exists for another tenant to give appropriate 404/403
        incident_any = IncidentManager.get_incident(incident_id)
        if incident_any and user_tenant and incident_any["tenant_id"] != user_tenant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Incident '{incident_id}' belongs to another tenant.",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )

    verify_tenant_boundary(user, incident["tenant_id"])
    return incident


@router.patch("/{incident_id}")
def update_incident(
    incident_id: str,
    req: UpdateIncidentStatusRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Update incident lifecycle status with RBAC enforcement and history recording.
    Requires SECURITY_ANALYST, SECURITY_RESPONDER, TENANT_ADMIN, or PLATFORM_ADMIN role.
    """
    user_role = user.get("role")
    if user_role not in ("SECURITY_ANALYST", "SECURITY_RESPONDER", "TENANT_ADMIN", "PLATFORM_ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{user_role}' is not authorized to update incident status. Requires analyst or responder privileges.",
        )

    user_tenant = user.get("tenant_id")
    incident = IncidentManager.get_incident(incident_id, tenant_id=user_tenant)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found for authorized tenant.",
        )

    try:
        updated = IncidentManager.update_incident_status(
            incident_id=incident_id,
            new_status=req.status,
            actor_id=user["user_id"],
            notes=req.notes,
            tenant_id=user_tenant,
        )
        return updated
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/{incident_id}/history")
def get_incident_history(
    incident_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Retrieve full timeline of state transitions and notes for an incident."""
    incident = IncidentManager.get_incident(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    verify_tenant_boundary(user, incident["tenant_id"])

    return IncidentManager.get_history(incident_id)


@router.get("/{incident_id}/recommendations")
def get_incident_recommendations(
    incident_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Retrieve recommended defensive actions for an incident."""
    incident = IncidentManager.get_incident(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    verify_tenant_boundary(user, incident["tenant_id"])

    return IncidentManager.get_recommendations(incident_id)
