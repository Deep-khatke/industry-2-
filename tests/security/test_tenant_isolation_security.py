"""Security test suite validating tenant isolation, input fuzzing, and secret hygiene."""

from pathlib import Path

import pytest

from adapters.memory.sink import MemoryStreamSink
from packages.observability.metrics import MetricsCollector
from packages.security.scanner import RepositorySecretScanner
from packages.tenancy.context import TenantContext
from packages.tenancy.exceptions import (
    CrossTenantAccessViolation,
    UntrustedTenantClaimViolation,
)
from packages.tenancy.models import Permission, Role, TenantId
from packages.tenancy.policy import PolicyEngine
from packages.tenancy.registry import TenantRegistry
from services.telemetry_collector.collector import TelemetryCollector
from tools.security_validation.validator import SecurityValidator
from tools.synthetic_exporter.generator import SyntheticTrafficGenerator


@pytest.mark.security
class TestSecurityAndTenantIsolation:
    """Rigorous security test suite verifying non-negotiable security constraints."""

    def test_cross_tenant_read_strictly_prevented(self) -> None:
        """Verify Tenant A analyst cannot read Tenant B telemetry."""
        ctx_a = TenantContext.create_for_user(
            user_id="analyst-alpha",
            role=Role.TENANT_ANALYST,
            tenant_id="tenant-isp-alpha",
        )
        target_b: TenantId = "tenant-isp-beta"

        with pytest.raises(CrossTenantAccessViolation):
            PolicyEngine.enforce_access(ctx_a, target_b, Permission.TELEMETRY_READ)

    def test_untrusted_telemetry_cannot_spoof_tenant(self) -> None:
        """
        Verify an incoming packet originating from Tenant A exporter cannot claim
        membership in Tenant B. The untrusted claim must be rejected.
        """
        registry = TenantRegistry.create_simulated_network()
        memory_sink = MemoryStreamSink()
        metrics = MetricsCollector()
        collector = TelemetryCollector(tenant_registry=registry, stream_sink=memory_sink, metrics=metrics)

        generator = SyntheticTrafficGenerator()
        # Normal stream for domain 101 (belonging to tenant-isp-alpha)
        packets = generator.generate_normal_stream(count=2, observation_domain_id=101)

        # Ingest first packet (template)
        collector.process_packet(packets[0].raw_bytes, source_ip="10.100.1.1")

        # Now forge packet with untrusted claim (e.g. attempting to claim tenant-isp-beta)
        # Even if a vendor tries to embed field 9999='tenant-isp-beta', normalizer rejects it
        from services.telemetry_collector.normalizer import TelemetryNormalizer

        raw_fields = {
            8: "10.100.1.10",
            12: "1.1.1.1",
            9999: "tenant-isp-beta",  # Untrusted claimed tenant
        }
        with pytest.raises(UntrustedTenantClaimViolation):
            TelemetryNormalizer.normalize_record(
                raw_fields=raw_fields,
                trusted_tenant_id="tenant-isp-alpha",
                exporter_id="gw-tenant-isp-alpha",
                observation_domain=101,
                boot_epoch=1,
                sequence=1,
                export_time_seconds=1700000000,
            )

    def test_unauthorized_exporter_ip_rejected(self) -> None:
        """Verify that telemetry from unregistered source IP is discarded with security metric."""
        registry = TenantRegistry.create_simulated_network()
        memory_sink = MemoryStreamSink()
        metrics = MetricsCollector()
        collector = TelemetryCollector(tenant_registry=registry, stream_sink=memory_sink, metrics=metrics)

        generator = SyntheticTrafficGenerator()
        packets = generator.generate_normal_stream(count=1, observation_domain_id=101)

        # Send from untrusted rogue IP (192.168.99.99)
        accepted = collector.process_packet(packets[0].raw_bytes, source_ip="192.168.99.99")
        assert len(accepted) == 0
        assert metrics.get_counter("events_rejected") == 1
        assert metrics.get_counter("tenant_scope_violations") == 1

    def test_fuzzing_resilience_random_bytes(self) -> None:
        """Verify that collector handles randomized garbage payloads without crashing or memory leaks."""
        registry = TenantRegistry.create_simulated_network()
        memory_sink = MemoryStreamSink()
        collector = TelemetryCollector(tenant_registry=registry, stream_sink=memory_sink)

        passed = SecurityValidator.verify_fuzzing_resilience(collector)
        assert passed is True

    def test_repository_contains_no_secrets(self) -> None:
        """Scan entire repository workspace for credentials or leaked API keys."""
        root = Path(__file__).resolve().parent.parent.parent
        scanner = RepositorySecretScanner(root_dir=root)
        result = scanner.scan_repository()

        assert result.scanned_files_count > 10
        assert result.passed is True, f"Found leaked secrets in repository: {result.findings}"
