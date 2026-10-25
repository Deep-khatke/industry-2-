"""Exceptions for multi-tenant isolation and security enforcement."""


class TenancyError(Exception):
    """Base exception for all tenancy-related errors."""


class TenantNotFoundError(TenancyError):
    """Raised when an operation references a tenant ID that does not exist."""

    def __init__(self, tenant_id: str) -> None:
        super().__init__(f"Tenant '{tenant_id}' does not exist in registry.")
        self.tenant_id = tenant_id


class InactiveTenantError(TenancyError):
    """Raised when attempting an operation on an inactive or suspended tenant."""

    def __init__(self, tenant_id: str, status: str) -> None:
        super().__init__(f"Tenant '{tenant_id}' is not active (status: {status}).")
        self.tenant_id = tenant_id
        self.status = status


class CrossTenantAccessViolation(TenancyError):
    """Raised when a principal attempts to read or mutate another tenant's data."""

    def __init__(
        self,
        principal_id: str,
        caller_tenant_id: str | None,
        target_tenant_id: str,
        action: str,
    ) -> None:
        super().__init__(
            f"Security violation: Principal '{principal_id}' (tenant: {caller_tenant_id}) "
            f"denied cross-tenant access to tenant '{target_tenant_id}' for action '{action}'."
        )
        self.principal_id = principal_id
        self.caller_tenant_id = caller_tenant_id
        self.target_tenant_id = target_tenant_id
        self.action = action


class UntrustedTenantClaimViolation(TenancyError):
    """Raised when untrusted telemetry metadata claims a tenant ID that conflicts with trusted origin."""

    def __init__(
        self,
        claimed_tenant_id: str,
        trusted_tenant_id: str,
        exporter_id: str,
    ) -> None:
        super().__init__(
            f"Security violation: Telemetry record claimed tenant '{claimed_tenant_id}', "
            f"but exporter '{exporter_id}' belongs to trusted tenant '{trusted_tenant_id}'. "
            f"Untrusted tenant claim rejected."
        )
        self.claimed_tenant_id = claimed_tenant_id
        self.trusted_tenant_id = trusted_tenant_id
        self.exporter_id = exporter_id


class UnauthorizedError(TenancyError):
    """Raised when a principal lacks required permissions within their authorized tenant."""

    def __init__(
        self,
        principal_id: str,
        tenant_id: str,
        required_permission: str,
    ) -> None:
        super().__init__(
            f"Principal '{principal_id}' lacks permission '{required_permission}' in tenant '{tenant_id}'."
        )
        self.principal_id = principal_id
        self.tenant_id = tenant_id
        self.required_permission = required_permission
