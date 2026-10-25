"""Base protocol and exceptions for stream sinks."""

from typing import Protocol, runtime_checkable

from packages.contracts.flow_event import FlowEvent


class SinkError(Exception):
    """Base exception for streaming sink operations."""


class SinkWriteError(SinkError):
    """Raised when writing to a stream sink fails."""


class SinkCapacityExceeded(SinkError):
    """Raised when a stream sink buffer or queue capacity is exceeded."""


@runtime_checkable
class StreamSink(Protocol):
    """Abstract interface for writing normalized FlowEvents into downstream queues/stores."""

    def write(self, event: FlowEvent) -> None:
        """Write a single FlowEvent to the sink."""
        ...

    def write_batch(self, events: list[FlowEvent]) -> int:
        """Write a batch of FlowEvents to the sink. Returns count of successfully accepted events."""
        ...

    def flush(self) -> None:
        """Flush any buffered events to persistent backing store."""
        ...

    def close(self) -> None:
        """Release underlying resources and close the sink."""
        ...
