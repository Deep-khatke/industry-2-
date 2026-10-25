"""Automated security validation runner."""

from dataclasses import dataclass
from typing import Any

from packages.tenancy.context import TenantContext
from packages.tenancy.exceptions import (
    CrossTenantAccessViolation,
    UnauthorizedError,
)
from packages.tenancy.models import Permission, Role, TenantId
from packages.tenancy.policy import PolicyEngine
from services.telemetry_collector.collector import TelemetryCollector


@dataclass
class SecurityVerificationSummary:
    """Consolidated summary of security and tenant isolation checks."""

    cross_tenant_access_blocked: bool
    untrusted_claim_spoofing_blocked: bool
    fuzzing_resilience_passed: bool
    secret_scan_passed: bool
    details: dict[str, Any]


class SecurityValidator:
    """Executes offline automated security regression suites."""

    @classmethod
    def verify_tenant_isolation(cls) -> bool:
        """Verify that Tenant A cannot access Tenant B's data under any condition."""
        ctx_a = TenantContext.create_for_user(
            user_id="analyst-a",
            role=Role.TENANT_ANALYST,
            tenant_id="tenant-isp-alpha",
        )
        target_b: TenantId = "tenant-isp-beta"

        # Attempt to read tenant B's telemetry
        try:
            PolicyEngine.enforce_access(ctx_a, target_b, Permission.TELEMETRY_READ)
            return False  # Failed: Access should have been denied
        except CrossTenantAccessViolation:
            return True  # Passed: Denied with typed violation

    @classmethod
    def verify_platform_admin_telemetry_isolation(cls) -> bool:
        """Verify that platform administrators cannot read raw tenant telemetry."""
        ctx_platform = TenantContext.create_for_user(
            user_id="plat-admin-1",
            role=Role.PLATFORM_ADMIN,
            tenant_id="tenant-isp-alpha",
        )
        try:
            PolicyEngine.enforce_access(ctx_platform, "tenant-isp-alpha", Permission.TELEMETRY_READ)
            return False  # Failed: Platform admin must NOT be able to read tenant telemetry
        except UnauthorizedError:
            return True

    @classmethod
    def verify_fuzzing_resilience(cls, collector: TelemetryCollector) -> bool:
        """Send truncated and randomized byte bursts; verify collector does not raise unhandled exceptions."""
        import random

        rng = random.Random(1337)
        for _ in range(50):
            length = rng.randint(0, 500)
            garbage = rng.randbytes(length)
            # Must return [] or handle safely without unhandled exception
            try:
                res = collector.process_packet(garbage, source_ip="10.100.1.1")
                assert isinstance(res, list)
            except Exception:
                return False
        return True
