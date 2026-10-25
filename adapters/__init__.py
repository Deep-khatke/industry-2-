"""Streaming adapters for telemetry ingestion pipelines."""

from .base import SinkCapacityExceeded, SinkError, SinkWriteError, StreamSink
from .memory.sink import MemoryStreamSink
from .sqlite.sink import SQLiteStreamSink

__all__ = [
    "MemoryStreamSink",
    "SQLiteStreamSink",
    "SinkCapacityExceeded",
    "SinkError",
    "SinkWriteError",
    "StreamSink",
]
