"""Coverage and exporter freshness tracker enforcing degraded state visibility."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class CoverageStatus(StrEnum):
    """Observability coverage health status for an exporter or tenant edge."""

    HEALTHY = "HEALTHY"        # Regular telemetry arriving within expected intervals
    DEGRADED = "DEGRADED"      # Packets dropping, sequence gaps observed, or late heartbeat
    UNKNOWN = "UNKNOWN"        # No telemetry received yet or exporter in unverified state
    DEAD = "DEAD"              # Exporter has stopped transmitting telemetry entirely


class ExporterHealth(BaseModel):
    """Health record for a specific exporter hardware endpoint."""

    exporter_id: str
    tenant_id: str
    last_seen: datetime | None = None
    packet_count: int = 0
    sequence_gaps: int = 0
    duplicate_count: int = 0
    status: CoverageStatus = CoverageStatus.UNKNOWN
    status_reason: str = "Awaiting initial telemetry."


class CoverageTracker:
    """Tracks exporter freshness and computes coverage health across ISP tenants."""

    def __init__(
        self,
        degraded_threshold_seconds: int = 30,
        dead_threshold_seconds: int = 120,
    ) -> None:
        self.degraded_threshold_seconds = degraded_threshold_seconds
        self.dead_threshold_seconds = dead_threshold_seconds
        # Key: (tenant_id, exporter_id) -> ExporterHealth
        self._exporters: dict[tuple[str, str], ExporterHealth] = {}

    def register_expected_exporter(self, tenant_id: str, exporter_id: str) -> None:
        """Register an anticipated exporter to guarantee missing telemetry is visible."""
        key = (tenant_id, exporter_id)
        if key not in self._exporters:
            self._exporters[key] = ExporterHealth(
                exporter_id=exporter_id,
                tenant_id=tenant_id,
                status=CoverageStatus.UNKNOWN,
                status_reason="Registered in topology, no telemetry received yet.",
            )

    def record_activity(
        self,
        tenant_id: str,
        exporter_id: str,
        sequence_gaps: int = 0,
        duplicates: int = 0,
        timestamp: datetime | None = None,
    ) -> CoverageStatus:
        """Update activity for an exporter and recompute its status."""
        key = (tenant_id, exporter_id)
        now = timestamp or datetime.now(UTC)
        if key not in self._exporters:
            self._exporters[key] = ExporterHealth(
                exporter_id=exporter_id,
                tenant_id=tenant_id,
            )

        exp = self._exporters[key]
        exp.last_seen = now
        exp.packet_count += 1
        exp.sequence_gaps += sequence_gaps
        exp.duplicate_count += duplicates

        if sequence_gaps > 0:
            exp.status = CoverageStatus.DEGRADED
            exp.status_reason = f"Detected {exp.sequence_gaps} sequence gap(s); potential packet loss."
        else:
            exp.status = CoverageStatus.HEALTHY
            exp.status_reason = "Telemetry transmitting normally."

        return exp.status

    def evaluate_all(self, reference_time: datetime | None = None) -> None:
        """Evaluate freshness of all exporters against thresholds."""
        now = reference_time or datetime.now(UTC)
        for exp in self._exporters.values():
            if exp.last_seen is None:
                exp.status = CoverageStatus.UNKNOWN
                exp.status_reason = "No telemetry received since registration."
                continue

            delta = (now - exp.last_seen).total_seconds()
            if delta > self.dead_threshold_seconds:
                exp.status = CoverageStatus.DEAD
                exp.status_reason = f"Telemetry ceased. Last seen {delta:.1f}s ago (> {self.dead_threshold_seconds}s threshold)."
            elif delta > self.degraded_threshold_seconds:
                exp.status = CoverageStatus.DEGRADED
                exp.status_reason = f"Delayed telemetry. Last seen {delta:.1f}s ago (> {self.degraded_threshold_seconds}s threshold)."
            elif exp.sequence_gaps > 0:
                exp.status = CoverageStatus.DEGRADED
                exp.status_reason = f"Observed {exp.sequence_gaps} sequence gap(s)."
            else:
                exp.status = CoverageStatus.HEALTHY
                exp.status_reason = "Telemetry transmitting normally."

    def get_tenant_coverage(
        self,
        tenant_id: str,
        reference_time: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Compute coverage summary for a tenant.
        CRITICAL ARCHITECTURE REQUIREMENT:
        Missing telemetry is explicitly presented as degraded or dead coverage.
        Absence of flow records is NEVER interpreted as absence of threats.
        """
        self.evaluate_all(reference_time=reference_time)
        tenant_exporters = [exp for (t_id, _), exp in self._exporters.items() if t_id == tenant_id]

        total = len(tenant_exporters)
        healthy = sum(1 for exp in tenant_exporters if exp.status == CoverageStatus.HEALTHY)
        degraded = sum(1 for exp in tenant_exporters if exp.status == CoverageStatus.DEGRADED)
        unknown = sum(1 for exp in tenant_exporters if exp.status == CoverageStatus.UNKNOWN)
        dead = sum(1 for exp in tenant_exporters if exp.status == CoverageStatus.DEAD)

        coverage_ratio = (healthy / total) if total > 0 else 0.0

        return {
            "tenant_id": tenant_id,
            "total_exporters": total,
            "healthy": healthy,
            "degraded": degraded,
            "unknown": unknown,
            "dead": dead,
            "coverage_ratio": coverage_ratio,
            "security_warning": (
                "DEGRADED_COVERAGE: Telemetry is incomplete. "
                "Absence of reported events must NOT be interpreted as absence of threats."
                if (degraded > 0 or unknown > 0 or dead > 0)
                else None
            ),
            "exporters": [exp.model_dump() for exp in tenant_exporters],
        }
