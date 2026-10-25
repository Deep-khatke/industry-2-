"""Zero-cost application metrics collector without external daemon dependencies."""

import threading
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any


class MetricsCollector:
    """Thread-safe in-memory metrics registry for Phase 1 telemetry pipelines."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._start_time = datetime.now(UTC)

    def increment(self, metric: str, value: int = 1, labels: dict[str, str] | None = None) -> None:
        """Increment a counter metric."""
        key = self._format_key(metric, labels)
        with self._lock:
            self._counters[key] += value

    def gauge(self, metric: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a point-in-time gauge metric."""
        key = self._format_key(metric, labels)
        with self._lock:
            self._gauges[key] = value

    def record_histogram(self, metric: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Record an observation in a histogram."""
        key = self._format_key(metric, labels)
        with self._lock:
            self._histograms[key].append(value)
            # Bound memory limit on histogram samples
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-500:]

    def get_counter(self, metric: str, labels: dict[str, str] | None = None) -> int:
        """Get current counter value."""
        key = self._format_key(metric, labels)
        with self._lock:
            return self._counters.get(key, 0)

    def get_gauge(self, metric: str, labels: dict[str, str] | None = None) -> float | None:
        """Get current gauge value."""
        key = self._format_key(metric, labels)
        with self._lock:
            return self._gauges.get(key)

    def snapshot(self) -> dict[str, Any]:
        """Produce an exportable snapshot of all current metrics."""
        with self._lock:
            summary: dict[str, Any] = {
                "collected_at": datetime.now(UTC).isoformat(),
                "uptime_seconds": (datetime.now(UTC) - self._start_time).total_seconds(),
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {},
            }
            for key, values in self._histograms.items():
                if values:
                    summary["histograms"][key] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                    }
                else:
                    summary["histograms"][key] = {"count": 0, "min": 0, "max": 0, "avg": 0}
            return summary

    def reset(self) -> None:
        """Reset all metric counters, gauges, and histograms."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._start_time = datetime.now(UTC)

    @staticmethod
    def _format_key(name: str, labels: dict[str, str] | None) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
