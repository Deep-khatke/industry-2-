"""Real-time flow telemetry ingestion pipeline and health tracker."""

from datetime import UTC, datetime
from typing import Any

from ..database import get_db
from ..detection.service import DetectionService
from ..incidents.manager import IncidentManager
from ..windows.engine import FeatureWindowEngine


class TelemetryIngestionPipeline:
    """
    Ingests network flow records, maps to tenant boundaries, processes event-time windows,
    executes detection and ML scoring, and triggers incident management.
    """

    def __init__(
        self,
        window_engine: FeatureWindowEngine | None = None,
        detection_service: DetectionService | None = None,
    ) -> None:
        self.window_engine = window_engine or FeatureWindowEngine()
        self.detection_service = detection_service or DetectionService()

    def ingest_record(self, raw_record: dict[str, Any]) -> dict[str, Any]:
        """Process a single incoming flow record end-to-end."""
        tenant_id = raw_record.get("tenant_id", "rural-isp-alpha")
        exporter_id = raw_record.get("exporter_id", "exp-alpha-core1")
        now_str = datetime.now(UTC).isoformat()

        # 1. Update Exporter Freshness in Database
        with get_db() as conn:
            conn.execute(
                """
                UPDATE exporters
                SET last_seen_at = ?, status = 'HEALTHY'
                WHERE exporter_id = ? AND tenant_id = ?
                """,
                (now_str, exporter_id, tenant_id),
            )

        # 2. Assign to Event-Time Window & Update Window Aggregates
        window_data = self.window_engine.process_flow_event(raw_record)
        if not window_data:
            return {"status": "DROPPED_LATE", "tenant_id": tenant_id}

        # 3. Execute Detection & Verified ML Inference
        detection_result = self.detection_service.analyze_window(
            window_data=window_data,
            flow_event=raw_record,
        )

        # 4. Process Incident & Recommendation Creation (with deduplication)
        incident = None
        if detection_result.get("is_threat"):
            incident = IncidentManager.process_detection(
                detection_result=detection_result,
                flow_event=raw_record,
                window_data=window_data,
            )

        return {
            "status": "PROCESSED",
            "tenant_id": tenant_id,
            "window_id": window_data.get("window_id"),
            "detection": detection_result,
            "incident_created": incident is not None,
            "incident": incident,
        }

    def ingest_batch(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Process a batch of incoming flow records."""
        return [self.ingest_record(r) for r in records]
