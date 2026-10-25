"""In-memory stream sink adapter for testing, fast validation, and fault injection."""

import random
import threading

from packages.contracts.flow_event import FlowEvent

from ..base import SinkCapacityExceeded, SinkWriteError, StreamSink


class MemoryStreamSink(StreamSink):
    """
    Thread-safe in-memory sink for unit tests, synthetic ingestion, and fault injection.
    Supports bounded capacity, synthetic errors, and tenant-scoped retrieval.
    """

    def __init__(self, max_capacity: int = 100_000) -> None:
        self.max_capacity = max_capacity
        self._lock = threading.Lock()
        self._events: list[FlowEvent] = []
        self._seen_event_ids: set[str] = set()
        self._duplicate_count: int = 0

        # Fault injection knobs
        self._fault_injection_active: bool = False
        self._fault_injection_message: str = "Simulated write failure"
        self._drop_probability: float = 0.0

    def set_fault_injection(self, active: bool, message: str = "Simulated write failure") -> None:
        """Enable or disable forced write exceptions."""
        with self._lock:
            self._fault_injection_active = active
            self._fault_injection_message = message

    def set_drop_probability(self, probability: float) -> None:
        """Set random drop probability between 0.0 and 1.0."""
        with self._lock:
            self._drop_probability = max(0.0, min(1.0, probability))

    def write(self, event: FlowEvent) -> None:
        with self._lock:
            if self._fault_injection_active:
                raise SinkWriteError(self._fault_injection_message)

            if self._drop_probability > 0.0 and random.random() < self._drop_probability:
                return  # Silently dropped for packet-loss / network-drop testing

            if len(self._events) >= self.max_capacity:
                raise SinkCapacityExceeded(
                    f"MemoryStreamSink reached max capacity of {self.max_capacity} events."
                )

            if event.event_id in self._seen_event_ids:
                self._duplicate_count += 1
                return  # Deduplicated

            self._seen_event_ids.add(event.event_id)
            self._events.append(event)

    def write_batch(self, events: list[FlowEvent]) -> int:
        accepted = 0
        for ev in events:
            self.write(ev)
            accepted += 1
        return accepted

    def flush(self) -> None:
        """No-op for in-memory buffer."""

    def close(self) -> None:
        """Close sink."""

    def get_events(self, tenant_id: str | None = None) -> list[FlowEvent]:
        """Retrieve stored events, optionally filtered by tenant."""
        with self._lock:
            if tenant_id is None:
                return list(self._events)
            return [e for e in self._events if e.tenant_id == tenant_id]

    def count(self, tenant_id: str | None = None) -> int:
        """Return count of stored events."""
        with self._lock:
            if tenant_id is None:
                return len(self._events)
            return sum(1 for e in self._events if e.tenant_id == tenant_id)

    @property
    def duplicate_count(self) -> int:
        with self._lock:
            return self._duplicate_count

    def clear(self) -> None:
        """Clear all stored events and reset duplicate counter."""
        with self._lock:
            self._events.clear()
            self._seen_event_ids.clear()
            self._duplicate_count = 0
