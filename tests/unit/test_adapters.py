"""Unit tests for stream sink adapters (Memory, SQLite, Kinesis stub)."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from adapters.aws.kinesis import KinesisStreamSink, SinkDisabledError
from adapters.base import SinkCapacityExceeded, SinkWriteError
from adapters.memory.sink import MemoryStreamSink
from adapters.sqlite.sink import SQLiteStreamSink
from packages.contracts.flow_event import FlowEvent


def create_sample_event(seq: int = 1, tenant_id: str = "tenant-isp-alpha") -> FlowEvent:
    now = datetime.now(UTC)
    return FlowEvent(
        tenant_id=tenant_id,
        exporter_id="gw-1",
        observation_domain=101,
        boot_epoch=1,
        sequence=seq,
        event_time=now,
        byte_count=1000,
        packet_count=5,
    )


@pytest.mark.unit
class TestStreamAdapters:
    """Test suite verifying streaming adapters."""

    def test_memory_sink_normal_and_deduplication(self) -> None:
        """Verify MemoryStreamSink stores events and deduplicates identical event IDs."""
        sink = MemoryStreamSink(max_capacity=100)
        e1 = create_sample_event(seq=1)
        e2 = create_sample_event(seq=2)

        sink.write(e1)
        sink.write(e2)
        assert sink.count() == 2

        # Write duplicate e1
        sink.write(e1)
        assert sink.count() == 2
        assert sink.duplicate_count == 1

        # Tenant filter
        assert len(sink.get_events(tenant_id="tenant-isp-alpha")) == 2
        assert len(sink.get_events(tenant_id="other-tenant")) == 0

    def test_memory_sink_capacity_exceeded(self) -> None:
        """Verify MemoryStreamSink enforces bounded capacity limits."""
        sink = MemoryStreamSink(max_capacity=2)
        sink.write(create_sample_event(seq=1))
        sink.write(create_sample_event(seq=2))

        with pytest.raises(SinkCapacityExceeded):
            sink.write(create_sample_event(seq=3))

    def test_memory_sink_fault_injection(self) -> None:
        """Verify simulated write exceptions trigger properly."""
        sink = MemoryStreamSink()
        sink.set_fault_injection(active=True, message="Simulated downstream Kinesis outage")

        with pytest.raises(SinkWriteError, match="downstream Kinesis outage"):
            sink.write(create_sample_event(seq=1))

    def test_sqlite_sink_persistence_and_restart(self, tmp_path: Path) -> None:
        """Verify SQLite sink stores events durably, survives restart, and retrieves correctly."""
        db_file = tmp_path / "test_telemetry.sqlite"
        sink = SQLiteStreamSink(db_path=db_file)

        e1 = create_sample_event(seq=10, tenant_id="tenant-isp-alpha")
        e2 = create_sample_event(seq=20, tenant_id="tenant-isp-beta")

        sink.write(e1)
        sink.write(e2)
        assert sink.count() == 2
        assert sink.count("tenant-isp-alpha") == 1

        # Simulate service restart: close connection and reopen existing file
        sink.close()
        restarted_sink = SQLiteStreamSink(db_path=db_file)
        assert restarted_sink.count() == 2

        alpha_events = restarted_sink.read_events(tenant_id="tenant-isp-alpha")
        assert len(alpha_events) == 1
        assert alpha_events[0].tenant_id == "tenant-isp-alpha"
        assert alpha_events[0].sequence == 10

        restarted_sink.close()

    def test_kinesis_sink_disabled_by_zero_cost_policy(self) -> None:
        """Verify KinesisStreamSink is disabled by default and raises SinkDisabledError."""
        sink = KinesisStreamSink()
        assert sink.enabled is False

        with pytest.raises(SinkDisabledError, match="DISABLED under the FCS Zero-Cost Policy"):
            sink.write(create_sample_event(seq=1))

    def test_kinesis_sink_offline_mock(self) -> None:
        """Verify KinesisStreamSink formats partition keys properly when using an injected mock client."""
        class MockKinesisClient:
            def __init__(self) -> None:
                self.records: list[dict[str, Any]] = []

            def put_record(self, **kwargs: Any) -> dict[str, Any]:
                self.records.append(kwargs)
                return {"SequenceNumber": "123", "ShardId": "shardId-000000000000"}

        mock_client = MockKinesisClient()
        sink = KinesisStreamSink(enabled=True, client=mock_client)

        event = create_sample_event(seq=42, tenant_id="tenant-isp-alpha")
        sink.write(event)

        assert len(mock_client.records) == 1
        rec = mock_client.records[0]
        # Verify tenant-scoped partition key
        assert rec["PartitionKey"] == f"tenant-isp-alpha#{event.exporter_id}"
        assert rec["StreamName"] == "fcs-telemetry-stream-dev"
