"""Integration tests verifying end-to-end synthetic packet ingestion and normalization."""

from pathlib import Path

import pytest

from adapters.memory.sink import MemoryStreamSink
from adapters.sqlite.sink import SQLiteStreamSink
from packages.observability.coverage import CoverageTracker
from packages.observability.metrics import MetricsCollector
from packages.tenancy.registry import TenantRegistry
from services.telemetry_collector.collector import CollectorConfig, TelemetryCollector
from tools.synthetic_exporter.generator import SyntheticTrafficGenerator
from tools.traffic_replay.replayer import TrafficReplayer


@pytest.mark.integration
class TestSyntheticIngestionPipeline:
    """End-to-end integration test of the telemetry pipeline."""

    def test_multi_tenant_synthetic_ingestion(self, tmp_path: Path) -> None:
        """
        Verify end-to-end flow from synthetic generator -> collector -> memory & sqlite sinks
        across multiple simulated rural ISPs.
        """
        registry = TenantRegistry.create_simulated_network()
        memory_sink = MemoryStreamSink()
        sqlite_file = tmp_path / "integration_test.sqlite"
        sqlite_sink = SQLiteStreamSink(db_path=sqlite_file)

        metrics = MetricsCollector()
        coverage = CoverageTracker()

        # Telemetry collector using Memory sink
        collector = TelemetryCollector(
            tenant_registry=registry,
            stream_sink=memory_sink,
            metrics=metrics,
            coverage=coverage,
            config=CollectorConfig(),
        )

        replayer = TrafficReplayer(collector=collector)
        generator = SyntheticTrafficGenerator(seed=777)

        # 1. Ingest telemetry from ISP Alpha (Observation Domain 101, IP 10.100.1.1)
        alpha_packets = generator.generate_normal_stream(count=15, observation_domain_id=101)
        summary_alpha = replayer.replay_packets(alpha_packets, source_ip="10.100.1.1")

        assert summary_alpha.accepted_events_count == 15
        assert memory_sink.count("tenant-isp-alpha") == 15

        # 2. Ingest telemetry from ISP Beta (Observation Domain 102, IP 10.100.2.1)
        beta_packets = generator.generate_normal_stream(count=10, observation_domain_id=102)
        summary_beta = replayer.replay_packets(beta_packets, source_ip="10.100.2.1")

        assert summary_beta.accepted_events_count == 10
        assert memory_sink.count("tenant-isp-beta") == 10

        # Verify total events in memory sink
        assert memory_sink.count() == 25

        # Verify privacy prefix masking on accepted events
        alpha_events = memory_sink.get_events(tenant_id="tenant-isp-alpha")
        for ev in alpha_events:
            assert ev.tenant_id == "tenant-isp-alpha"
            assert ev.src_prefix_masked is not None
            assert ev.src_prefix_masked.endswith("/24")
            # Verify no raw host IP is stored
            assert not ev.src_prefix_masked.startswith("10.100.1.50/32")

        # 3. Dual-write to SQLite sink to verify persistent zero-cost storage
        sqlite_sink.write_batch(alpha_events)
        assert sqlite_sink.count("tenant-isp-alpha") == 15
        sqlite_sink.close()

        # 4. Check pipeline metrics
        assert metrics.get_counter("events_accepted") == 25
        assert metrics.get_counter("events_rejected") == 0
        assert metrics.get_counter("tenant_scope_violations") == 0
