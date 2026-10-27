"""Threat Detection and ML Models status API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth.dependencies import get_current_user
from ..detection.service import DetectionService

router = APIRouter(prefix="/v1", tags=["Detection & Models"])

# Singleton detection service instance
_detection_service: DetectionService | None = None


def get_detection_service() -> DetectionService:
    global _detection_service
    if _detection_service is None:
        _detection_service = DetectionService()
    return _detection_service


@router.get("/detection/status")
def get_detection_status(
    _user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve operational detection rules, thresholds, and scoring engine configuration."""
    service = get_detection_service()
    model_health = service.get_model_health()

    return {
        "engine_version": "v1.2.0",
        "detection_mode": "HYBRID_ML_RULES",
        "ml_model_status": model_health["status"],
        "active_model_id": model_health["model_id"],
        "fallback_mode": model_health["fallback_mode"],
        "detection_rules": [
            {
                "rule_id": "FCS-R101",
                "name": "Volumetric Flood / DDoS Burst",
                "category": "DDoS",
                "thresholds": "in_bytes > 500,000 OR in_pkts > 2,500 OR flow_count > 80",
                "severity": "CRITICAL / HIGH",
            },
            {
                "rule_id": "FCS-R102",
                "name": "SYN Port Scanning / Reconnaissance",
                "category": "PortScan",
                "thresholds": "tcp_flags == 2 (SYN) AND in_pkts < 10",
                "severity": "MEDIUM",
            },
            {
                "rule_id": "FCS-R103",
                "name": "Abnormal Flow Duration / Slowloris Keepalive",
                "category": "DoS",
                "thresholds": "flow_duration_ms > 60,000 AND in_bytes < 5,000",
                "severity": "LOW",
            },
            {
                "rule_id": "FCS-R104",
                "name": "High-Risk Service Probe",
                "category": "Reconnaissance",
                "thresholds": "dst_port IN [23, 2323, 445, 3389, 5060]",
                "severity": "MEDIUM",
            },
        ],
        "risk_levels": ["INFORMATIONAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"],
        "ml_thresholds": {
            "critical": 0.85,
            "high": 0.70,
            "medium": 0.50,
            "low": 0.30,
        },
    }


@router.get("/models/active")
def get_active_model(
    _user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve active candidate ML model metadata, provenance, and deployable feature contract."""
    service = get_detection_service()
    health = service.get_model_health()

    return {
        "model_id": health["model_id"],
        "status": health["status"],
        "model_type": "LightGBMClassifier",
        "training_phase": "Phase 3 (Validated)",
        "pr_auc": 0.9530,
        "f1_score": 0.8872,
        "inference_latency_p95_ms": 0.456,
        "deployable_feature_count": 14,
        "deployable_feature_schema": [
            {"name": "IN_BYTES", "type": "INTEGER", "description": "Incoming byte volume"},
            {"name": "OUT_BYTES", "type": "INTEGER", "description": "Outgoing byte volume"},
            {"name": "IN_PKTS", "type": "INTEGER", "description": "Incoming packet count"},
            {"name": "OUT_PKTS", "type": "INTEGER", "description": "Outgoing packet count"},
            {"name": "FLOW_DURATION_MILLISECONDS", "type": "FLOAT", "description": "Total flow duration in milliseconds"},
            {"name": "TCP_FLAGS", "type": "INTEGER", "description": "Cumulative TCP control flags"},
            {"name": "L4_SRC_PORT", "type": "INTEGER", "description": "Layer 4 source port"},
            {"name": "L4_DST_PORT", "type": "INTEGER", "description": "Layer 4 destination port"},
            {"name": "PROTOCOL", "type": "INTEGER", "description": "IANA IP protocol number"},
            {"name": "DURATION_IN", "type": "FLOAT", "description": "Duration ingress component"},
            {"name": "DURATION_OUT", "type": "FLOAT", "description": "Duration egress component"},
            {"name": "SRC_TO_DST_SECOND_BYTES", "type": "FLOAT", "description": "Forward byte rate per second"},
            {"name": "DST_TO_SRC_SECOND_BYTES", "type": "FLOAT", "description": "Reverse byte rate per second"},
            {"name": "NUM_PKTS_UP_TO_128_BYTES", "type": "INTEGER", "description": "Count of small packets"},
        ],
        "zero_cost_runtime": "Local CPU (ONNX / LightGBM)",
        "security_invariant": "network_action_executed = False",
    }


@router.get("/models/health")
def get_models_health(
    _user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve live inference health, error states, and runtime resource limits."""
    service = get_detection_service()
    return service.get_model_health()


@router.get("/detection/bundle")
def get_detection_bundle(
    _user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve the currently active DetectionBundle, constituent models, and SHA-256 digests."""
    service = get_detection_service()
    return service.get_active_bundle()


@router.post("/detection/bundle/activate")
def activate_detection_bundle(
    payload: dict[str, Any],
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Authorized activation of an ensemble DetectionBundle (requires TENANT_ADMIN or PLATFORM_ADMIN)."""
    service = get_detection_service()
    role = user.get("role", "READ_ONLY")
    actor_id = user.get("user_id", "unknown_user")
    try:
        return service.activate_bundle(payload, actor_id=actor_id, role=role)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        return {"success": False, "message": f"Bundle validation failed: {str(e)}"}


@router.post("/detection/bundle/rollback")
def rollback_detection_bundle(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Rollback to the previously active verified detection bundle."""
    service = get_detection_service()
    role = user.get("role", "READ_ONLY")
    actor_id = user.get("user_id", "unknown_user")
    try:
        return service.rollback_bundle(actor_id=actor_id, role=role)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/detection/models")
def get_registered_models(
    _user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Retrieve all candidate models and specialist classifiers in the candidate registry."""
    service = get_detection_service()
    return service.list_registered_models()


@router.get("/detection/routing-decisions")
def get_routing_decisions(
    limit: int = 50,
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Retrieve recent conditional routing decisions for the authenticated tenant."""
    service = get_detection_service()
    tenant_id = user.get("tenant_id") or "rural-isp-alpha"
    return service.get_routing_decisions(tenant_id=tenant_id, limit=limit)


@router.get("/detection/isp-anomaly-status")
def get_isp_anomaly_status(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve anomaly detection baseline status and tenancy isolation verification."""
    service = get_detection_service()
    tenant_id = user.get("tenant_id") or "rural-isp-alpha"
    return service.get_isp_anomaly_status(tenant_id=tenant_id)

