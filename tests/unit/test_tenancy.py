"""Unit tests for multi-tenant identity, RBAC authorization, and audit logging."""

import pytest

from packages.tenancy.audit import AuditLogger
from packages.tenancy.context import TenantContext
from packages.tenancy.exceptions import (
    CrossTenantAccessViolation,
    UnauthorizedError,
    UntrustedTenantClaimViolation,
)
from packages.tenancy.models import (
    Permission,
    Role,
)
from packages.tenancy.policy import PolicyEngine
from packages.tenancy.registry import TenantRegistry


@pytest.mark.unit
class TestTenancyAndAuthorization:
    """Test suite verifying tenancy models, registry, and RBAC policies."""

    def test_tenant_registry_simulation(self) -> None:
        """Verify the 7 simulated rural ISPs are registered and resolvable."""
        registry = TenantRegistry.create_simulated_network()
        tenants = registry.list_tenants()
        assert len(tenants) == 7

        # Check resolution for Northern Valley Broadband (Alpha)
        resolved = registry.resolve_exporter("10.100.1.1", 101)
        assert resolved is not None
        tenant_id, exporter_id = resolved
        assert tenant_id == "tenant-isp-alpha"
        assert exporter_id == "gw-tenant-isp-alpha"

        # Check unknown exporter returns None
        assert registry.resolve_exporter("192.168.1.1", 999) is None

    def test_untrusted_tenant_claim_rejected(self) -> None:
        """Verify that telemetry claiming a mismatched tenant is rejected."""
        registry = TenantRegistry.create_simulated_network()
        with pytest.raises(UntrustedTenantClaimViolation):
            registry.validate_telemetry_origin(
                trusted_tenant_id="tenant-isp-alpha",
                exporter_id="gw-tenant-isp-alpha",
                untrusted_claimed_tenant_id="tenant-isp-beta",
            )

        # Matching claim passes
        assert (
            registry.validate_telemetry_origin(
                trusted_tenant_id="tenant-isp-alpha",
                exporter_id="gw-tenant-isp-alpha",
                untrusted_claimed_tenant_id="tenant-isp-alpha",
            )
            == "tenant-isp-alpha"
        )

    def test_tenant_analyst_permissions(self) -> None:
        """Verify Tenant Analyst can read their own tenant's data but cannot manage tenant."""
        ctx = TenantContext.create_for_user(
            user_id="analyst-1",
            role=Role.TENANT_ANALYST,
            tenant_id="tenant-isp-alpha",
        )

        # Allowed
        PolicyEngine.enforce_access(ctx, "tenant-isp-alpha", Permission.TELEMETRY_READ)

        # Disallowed: Lacks tenant manage permission
        with pytest.raises(UnauthorizedError):
            PolicyEngine.enforce_access(ctx, "tenant-isp-alpha", Permission.TENANT_MANAGE)

    def test_cross_tenant_access_strictly_blocked(self) -> None:
        """Verify Tenant A cannot access Tenant B's resources."""
        ctx_a = TenantContext.create_for_user(
            user_id="admin-a",
            role=Role.TENANT_ADMIN,
            tenant_id="tenant-isp-alpha",
        )

        with pytest.raises(CrossTenantAccessViolation):
            PolicyEngine.enforce_access(ctx_a, "tenant-isp-beta", Permission.TELEMETRY_READ)

    def test_platform_admin_cannot_access_tenant_telemetry(self) -> None:
        """
        CRITICAL ARCHITECTURAL CONSTRAINT:
        Platform administrators must NOT obtain unrestricted tenant telemetry access.
        """
        ctx_platform = TenantContext.create_for_user(
            user_id="super-admin",
            role=Role.PLATFORM_ADMIN,
            tenant_id="tenant-isp-alpha",
        )

        # Can manage tenants
        allowed, reason = PolicyEngine.evaluate_access(
            ctx_platform, "tenant-isp-alpha", Permission.TENANT_MANAGE
        )
        assert allowed is True

        # CANNOT read raw telemetry
        allowed, reason = PolicyEngine.evaluate_access(
            ctx_platform, "tenant-isp-alpha", Permission.TELEMETRY_READ
        )
        assert allowed is False
        assert "strictly prohibited" in reason

        with pytest.raises(UnauthorizedError):
            PolicyEngine.enforce_access(
                ctx_platform, "tenant-isp-alpha", Permission.TELEMETRY_READ
            )

    def test_audit_logger_cryptographic_chain(self) -> None:
        """Verify audit logger generates tamper-evident SHA-256 chain."""
        audit = AuditLogger()
        audit.log("user-1", "read", "telemetry/alpha", "ALLOWED", tenant_id="tenant-isp-alpha")
        audit.log("user-2", "read", "telemetry/beta", "DENIED", tenant_id="tenant-isp-beta")
        audit.log("user-3", "export", "telemetry/gamma", "ALLOWED", tenant_id="tenant-isp-gamma")

        valid, msg = audit.verify_integrity()
        assert valid is True
        assert "intact" in msg

        records = audit.get_records()
        assert len(records) == 3

        # Tampering detection test
        records[1].action = "tampered_action"
        valid_after_tamper, tamper_msg = audit.verify_integrity()
        assert valid_after_tamper is False
        assert "tampered" in tamper_msg
