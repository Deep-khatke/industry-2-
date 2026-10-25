"""Generates human-readable Markdown and structured JSON verification reports."""

import json
from typing import Any

from .coverage import CoverageTracker
from .metrics import MetricsCollector


class MetricsReporter:
    """Renders test and runtime metrics into audit summaries."""

    def __init__(self, metrics: MetricsCollector, coverage: CoverageTracker) -> None:
        self.metrics = metrics
        self.coverage = coverage

    def render_markdown_dashboard(self) -> str:
        """Render markdown dashboard table showing metrics and coverage health."""
        snap = self.metrics.snapshot()
        counters = snap.get("counters", {})
        gauges = snap.get("gauges", {})

        md_lines = [
            "# FCS Phase 1 Observability & Ingestion Verification Dashboard",
            f"**Generated at:** {snap.get('collected_at')} | **Uptime:** {snap.get('uptime_seconds', 0.0):.2f}s",
            "",
            "## Ingestion Metrics",
            "| Metric | Count | Description |",
            "|---|---|---|",
            f"| `events_accepted` | {counters.get('events_accepted', 0)} | Validated FlowEvent objects accepted into stream |",
            f"| `events_rejected` | {counters.get('events_rejected', 0)} | Malformed or schema-invalid events rejected |",
            f"| `duplicate_events` | {counters.get('duplicate_events', 0)} | Redundant duplicate events deduplicated |",
            f"| `sequence_gaps` | {counters.get('sequence_gaps', 0)} | Observable packet drop sequence discontinuities |",
            f"| `invalid_templates` | {counters.get('invalid_templates', 0)} | Unknown or corrupted IPFIX template IDs |",
            f"| `tenant_scope_violations` | {counters.get('tenant_scope_violations', 0)} | Cross-tenant access or spoofing attempts blocked |",
            f"| `stream_write_failures` | {counters.get('stream_write_failures', 0)} | Storage or streaming adapter write exceptions |",
            "",
            "## Runtime Gauges",
            "| Gauge | Value |",
            "|---|---|",
            f"| Active Exporters | {gauges.get('active_exporters', 0)} |",
            f"| Degraded Coverage Nodes | {gauges.get('degraded_coverage_count', 0)} |",
            f"| Memory Buffer Utilization | {gauges.get('memory_buffer_utilization_pct', 0.0):.1f}% |",
            "",
        ]
        return "\n".join(md_lines)

    def export_json(self) -> str:
        """Export metrics and coverage data as structured JSON."""
        data: dict[str, Any] = {
            "metrics": self.metrics.snapshot(),
        }
        return json.dumps(data, indent=2)
