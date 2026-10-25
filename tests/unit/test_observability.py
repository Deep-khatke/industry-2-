"""Unit tests for observability, metrics collection, and coverage tracking."""

from datetime import UTC, datetime, timedelta

import pytest

from packages.observability.coverage import CoverageTracker
from packages.observability.logger import sanitize_sensitive_data
from packages.observability.metrics import MetricsCollector
from packages.observability.reporter import MetricsReporter


@pytest.mark.unit
class TestObservabilityAndCoverage:
    """Test suite verifying observability, metrics, and degraded coverage semantics."""

    def test_log_sanitization_redacts_secrets_and_masks_ips(self) -> None:
        """Verify sensitive credentials are removed and IP addresses masked."""
        data = {
            "api_key": "secret-value-123",
            "password": "super-secret-pass",
            "user_token": "bearer-token-456",
            "subscriber_ip": "198.51.100.89",
            "safe_metric": 42,
        }
        sanitized = sanitize_sensitive_data(data)

        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["user_token"] == "[REDACTED]"
        assert sanitized["subscriber_ip"] == "198.51.xxx.xxx"
        assert sanitized["safe_metric"] == 42

    def test_metrics_collector_counters_and_gauges(self) -> None:
        """Verify thread-safe metric counter and gauge operations."""
        metrics = MetricsCollector()
        metrics.increment("events_accepted", 10)
        metrics.increment("events_accepted", 5)
        metrics.increment("sequence_gaps", 2)
        metrics.gauge("active_exporters", 7.0)
        metrics.record_histogram("processing_latency_ms", 12.5)
        metrics.record_histogram("processing_latency_ms", 18.0)

        assert metrics.get_counter("events_accepted") == 15
        assert metrics.get_counter("sequence_gaps") == 2
        assert metrics.get_gauge("active_exporters") == 7.0

        snap = metrics.snapshot()
        assert snap["counters"]["events_accepted"] == 15
        assert snap["gauges"]["active_exporters"] == 7.0
        hist = snap["histograms"]["processing_latency_ms"]
        assert hist["count"] == 2
        assert hist["avg"] == 15.25

    def test_coverage_tracker_missing_telemetry_is_degraded_not_zero_threat(self) -> None:
        """
        CRITICAL ARCHITECTURAL CONSTRAINT:
        Missing telemetry must appear as degraded or dead coverage.
        Absence of flow events must NOT be interpreted as absence of threats.
        """
        tracker = CoverageTracker(degraded_threshold_seconds=10, dead_threshold_seconds=30)
        tracker.register_expected_exporter(tenant_id="tenant-isp-alpha", exporter_id="gw-alpha-1")
        tracker.register_expected_exporter(tenant_id="tenant-isp-alpha", exporter_id="gw-alpha-2")

        # Initial state before telemetry arrives: UNKNOWN
        summary = tracker.get_tenant_coverage("tenant-isp-alpha")
        assert summary["total_exporters"] == 2
        assert summary["unknown"] == 2
        assert summary["healthy"] == 0
        assert summary["security_warning"] is not None
        assert "DEGRADED_COVERAGE" in summary["security_warning"]

        # Telemetry arrives from gw-alpha-1
        now = datetime.now(UTC)
        tracker.record_activity("tenant-isp-alpha", "gw-alpha-1", sequence_gaps=0, timestamp=now)

        summary2 = tracker.get_tenant_coverage("tenant-isp-alpha")
        assert summary2["healthy"] == 1
        assert summary2["unknown"] == 1  # gw-alpha-2 is still unknown
        assert summary2["security_warning"] is not None

        # Sequence gap on gw-alpha-1 degrades it
        tracker.record_activity("tenant-isp-alpha", "gw-alpha-1", sequence_gaps=3, timestamp=now)
        summary3 = tracker.get_tenant_coverage("tenant-isp-alpha")
        assert summary3["degraded"] == 1

        # Simulate time jump: telemetry ceased (> 30s) -> transitions to DEAD
        future_time = now + timedelta(seconds=45)
        summary4 = tracker.get_tenant_coverage("tenant-isp-alpha", reference_time=future_time)
        assert summary4["dead"] == 1

    def test_metrics_reporter_dashboard_rendering(self) -> None:
        """Verify reporter renders markdown dashboard."""
        metrics = MetricsCollector()
        metrics.increment("events_accepted", 100)
        metrics.increment("sequence_gaps", 3)
        coverage = CoverageTracker()

        reporter = MetricsReporter(metrics, coverage)
        md = reporter.render_markdown_dashboard()

        assert "FCS Phase 1 Observability & Ingestion Verification Dashboard" in md
        assert "`events_accepted` | 100" in md
        assert "`sequence_gaps` | 3" in md

        json_out = reporter.export_json()
        assert '"events_accepted": 100' in json_out
