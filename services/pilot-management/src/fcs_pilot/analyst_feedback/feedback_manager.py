"""Analyst Incident Review and Feedback Management System."""

import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger("fcs_pilot.analyst_feedback")


class IncidentDisposition(StrEnum):
    """Supported human analyst triage dispositions."""
    TRUE_POSITIVE = "TRUE_POSITIVE"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    BENIGN_BUT_UNUSUAL = "BENIGN_BUT_UNUSUAL"
    INCONCLUSIVE = "INCONCLUSIVE"
    NEEDS_FURTHER_INVESTIGATION = "NEEDS_FURTHER_INVESTIGATION"
    DUPLICATE = "DUPLICATE"
    UNSUPPORTED_CLASSIFICATION = "UNSUPPORTED_CLASSIFICATION"


class AnalystFeedbackRecord(BaseModel):
    """Structured record of human analyst review for a detected threat incident."""
    feedback_id: str
    incident_id: str
    tenant_id: str
    analyst_id: str
    analyst_role: str
    review_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    disposition: IncidentDisposition
    evidence_refs: list[str] = Field(default_factory=list)
    review_duration_seconds: float = Field(..., description="Time taken by analyst to investigate incident")
    confidence_level: float = Field(default=1.0, ge=0.0, le=1.0)
    notes: str = Field(default="")
    model_version: str = Field(default="1.2.0")
    review_state: str = Field(default="SUBMITTED")


class AnalystFeedbackManager:
    """Manages recording, tenant scoping, and aggregation of human triage feedback."""

    def __init__(self) -> None:
        self._records: list[AnalystFeedbackRecord] = []

    def submit_feedback(
        self,
        incident_id: str,
        tenant_id: str,
        analyst_id: str,
        analyst_role: str,
        disposition: IncidentDisposition,
        review_duration_seconds: float,
        notes: str,
        evidence_refs: list[str] | None = None,
        confidence_level: float = 1.0,
        model_version: str = "1.2.0",
    ) -> AnalystFeedbackRecord:
        """
        Record verified analyst triage feedback with tenant boundaries enforced.
        """
        # Role check
        if analyst_role not in ("SECURITY_ANALYST", "SECURITY_RESPONDER", "TENANT_ADMIN", "PLATFORM_ADMIN"):
            raise PermissionError(f"Role '{analyst_role}' is not authorized to submit incident triage feedback.")

        if review_duration_seconds < 0:
            raise ValueError("Review duration cannot be negative.")

        fid = f"fb-{tenant_id[:4]}-{len(self._records) + 1:04d}"
        record = AnalystFeedbackRecord(
            feedback_id=fid,
            incident_id=incident_id,
            tenant_id=tenant_id,
            analyst_id=analyst_id,
            analyst_role=analyst_role,
            disposition=disposition,
            evidence_refs=evidence_refs or [],
            review_duration_seconds=review_duration_seconds,
            confidence_level=confidence_level,
            notes=notes,
            model_version=model_version,
            review_state="SUBMITTED",
        )
        self._records.append(record)
        logger.info(f"Recorded analyst feedback {fid} for incident {incident_id} ({disposition}) by {analyst_id}.")
        return record

    def get_feedback_for_tenant(self, tenant_id: str) -> list[AnalystFeedbackRecord]:
        """Tenant-isolated retrieval: never leaks feedback across tenants."""
        return [r for r in self._records if r.tenant_id == tenant_id]

    def get_feedback_for_incident(self, incident_id: str, tenant_id: str) -> AnalystFeedbackRecord | None:
        for r in self._records:
            if r.incident_id == incident_id and r.tenant_id == tenant_id:
                return r
        return None

    def get_triage_statistics(self, tenant_id: str) -> dict[str, Any]:
        """Compute triage workload and accuracy metrics for a specific tenant."""
        tenant_recs = self.get_feedback_for_tenant(tenant_id)
        if not tenant_recs:
            return {
                "tenant_id": tenant_id,
                "total_reviewed": 0,
                "true_positives": 0,
                "false_positives": 0,
                "benign_unusual": 0,
                "inconclusive": 0,
                "avg_review_duration_seconds": 0.0,
                "total_review_minutes": 0.0,
            }

        tps = sum(1 for r in tenant_recs if r.disposition == IncidentDisposition.TRUE_POSITIVE)
        fps = sum(1 for r in tenant_recs if r.disposition == IncidentDisposition.FALSE_POSITIVE)
        benign = sum(1 for r in tenant_recs if r.disposition == IncidentDisposition.BENIGN_BUT_UNUSUAL)
        inconc = sum(1 for r in tenant_recs if r.disposition == IncidentDisposition.INCONCLUSIVE)
        total_sec = sum(r.review_duration_seconds for r in tenant_recs)

        return {
            "tenant_id": tenant_id,
            "total_reviewed": len(tenant_recs),
            "true_positives": tps,
            "false_positives": fps,
            "benign_unusual": benign,
            "inconclusive": inconc,
            "avg_review_duration_seconds": round(total_sec / len(tenant_recs), 1),
            "total_review_minutes": round(total_sec / 60.0, 1),
        }
