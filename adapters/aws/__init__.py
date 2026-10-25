"""AWS cloud integration adapters (Deferred / Offline Mode for Phase 1)."""

from .kinesis import KinesisStreamSink, SinkDisabledError

__all__ = ["KinesisStreamSink", "SinkDisabledError"]
