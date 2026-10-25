"""Fault injection and resilience test suite."""

import pytest

from adapters.memory.sink import MemoryStreamSink
from packages.observability.coverage import CoverageTracker
from packages.observability.metrics import MetricsCollector
from packages.tenancy.registry import TenantRegistry
from services.telemetry_collector.collector import TelemetryCollector
from tools.synthetic_exporter.generator import SyntheticTrafficGenerator, TrafficScenario


@pytest.mark.fault_injection
class TestFaultInjectionScenarios:
    """Test suite verifying robustness under synthetic network anomalies and corruptions."""

    def test_missing_and_unknown_template_fault(self) -> None:
        """Verify data records referencing unknown templates are safely skipped and counted."""
        registry = TenantRegistry.create_simulated_network()
        sink = MemoryStreamSink()
        metrics = MetricsCollector()
        collector = TelemetryCollector(tenant_registry=registry, stream_sink=sink, metrics=metrics)

        generator = SyntheticTrafficGenerator(seed=101)
        fault_packets = generator.generate_fault_scenario(
            scenario=TrafficScenario.UNKNOWN_TEMPLATE_FAULT,
            observation_domain_id=101,
        )

        for pkt in fault_packets:
            collector.process_packet(pkt.raw_bytes, source_ip="10.100.1.1")

        # Unknown template was encountered and counted
        assert metrics.get_counter("invalid_templates") >= 1
        # Collector did not crash and accepted normal records
        assert sink.count("tenant-isp-alpha") >= 5

    def test_sequence_gap_fault(self) -> None:
        """Verify sequence jump is detected as sequence gap and flags coverage as degraded."""
        registry = TenantRegistry.create_simulated_network()
        sink = MemoryStreamSink()
        metrics = MetricsCollector()
        coverage = CoverageTracker()
        collector = TelemetryCollector(
            tenant_registry=registry,
            stream_sink=sink,
            metrics=metrics,
            coverage=coverage,
        )

        generator = SyntheticTrafficGenerator(seed=202)
        fault_packets = generator.generate_fault_scenario(
            scenario=TrafficScenario.SEQUENCE_GAP_FAULT,
            observation_domain_id=101,
        )

        for pkt in fault_packets:
            collector.process_packet(pkt.raw_bytes, source_ip="10.100.1.1")

        assert metrics.get_counter("sequence_gaps") >= 5

        # Check coverage status for ISP Alpha
        cov = coverage.get_tenant_coverage("tenant-isp-alpha")
        assert cov["degraded"] >= 1
        assert cov["security_warning"] is not None

    def test_duplicate_packets_fault(self) -> None:
        """Verify duplicate packets are counted and deduplicated."""
        registry = TenantRegistry.create_simulated_network()
        sink = MemoryStreamSink()
        metrics = MetricsCollector()
        collector = TelemetryCollector(tenant_registry=registry, stream_sink=sink, metrics=metrics)

        generator = SyntheticTrafficGenerator(seed=303)
        fault_packets = generator.generate_fault_scenario(
            scenario=TrafficScenario.DUPLICATE_FLOW_FAULT,
            observation_domain_id=101,
        )

        for pkt in fault_packets:
            collector.process_packet(pkt.raw_bytes, source_ip="10.100.1.1")

        assert metrics.get_counter("duplicate_events") >= 1
        # Sink deduplicated event
        assert sink.duplicate_count >= 1

    def test_exporter_restart_fault(self) -> None:
        """Verify exporter reboot sequence reset is handled smoothly."""
        registry = TenantRegistry.create_simulated_network()
        sink = MemoryStreamSink()
        metrics = MetricsCollector()
        collector = TelemetryCollector(tenant_registry=registry, stream_sink=sink, metrics=metrics)

        generator = SyntheticTrafficGenerator(seed=404)
        fault_packets = generator.generate_fault_scenario(
            scenario=TrafficScenario.EXPORTER_RESTART_FAULT,
            observation_domain_id=101,
        )

        for pkt in fault_packets:
            collector.process_packet(pkt.raw_bytes, source_ip="10.100.1.1")

        # Collector continued accepting packets after restart
        assert sink.count("tenant-isp-alpha") >= 5

    def test_corrupted_packet_fault(self) -> None:
        """Verify truncated and malformed length packets are safely rejected."""
        registry = TenantRegistry.create_simulated_network()
        sink = MemoryStreamSink()
        metrics = MetricsCollector()
        collector = TelemetryCollector(tenant_registry=registry, stream_sink=sink, metrics=metrics)

        generator = SyntheticTrafficGenerator(seed=505)
        fault_packets = generator.generate_fault_scenario(
            scenario=TrafficScenario.CORRUPTED_PACKET_FAULT,
            observation_domain_id=101,
        )

        for pkt in fault_packets:
            collector.process_packet(pkt.raw_bytes, source_ip="10.100.1.1")

        assert metrics.get_counter("packets_corrupted") >= 1
        assert metrics.get_counter("events_rejected") >= 1
