"""Policy engine and role-based access control with strict tenant isolation."""

from .context import TenantContext
from .exceptions import CrossTenantAccessViolation, UnauthorizedError
from .models import Permission, Role, TenantId

# Strict RBAC permission matrix
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.TENANT_ADMIN: {
        Permission.TELEMETRY_INGEST,
        Permission.TELEMETRY_READ,
        Permission.TELEMETRY_EXPORT,
        Permission.AUDIT_READ,
        Permission.AUDIT_WRITE,
        Permission.TENANT_MANAGE,
        Permission.POLICY_EVALUATE,
        Permission.INCIDENT_READ,
        Permission.INCIDENT_WRITE,
        Permission.RESPONSE_READ,
        Permission.RESPONSE_APPROVE,
    },
    Role.TENANT_ANALYST: {
        Permission.TELEMETRY_READ,
        Permission.TELEMETRY_EXPORT,
        Permission.AUDIT_READ,
        Permission.INCIDENT_READ,
        Permission.INCIDENT_WRITE,
        Permission.RESPONSE_READ,
    },
    Role.SECURITY_ANALYST: {
        Permission.TELEMETRY_READ,
        Permission.AUDIT_READ,
        Permission.INCIDENT_READ,
        Permission.INCIDENT_WRITE,
        Permission.RESPONSE_READ,
    },
    Role.SECURITY_RESPONDER: {
        Permission.TELEMETRY_READ,
        Permission.AUDIT_READ,
        Permission.INCIDENT_READ,
        Permission.RESPONSE_READ,
        Permission.RESPONSE_APPROVE,
    },
    Role.READ_ONLY: {
        Permission.TELEMETRY_READ,
        Permission.AUDIT_READ,
        Permission.INCIDENT_READ,
        Permission.RESPONSE_READ,
    },
    Role.TENANT_EXPORTER: {
        Permission.TELEMETRY_INGEST,
    },
    Role.PLATFORM_ADMIN: {
        Permission.TENANT_MANAGE,
        Permission.AUDIT_READ,
        Permission.AUDIT_WRITE,
        Permission.POLICY_EVALUATE,
    },
    Role.PLATFORM_AUDITOR: {
        Permission.AUDIT_READ,
    },
}


class PolicyEngine:
    """Evaluates access requests against tenant boundaries and RBAC permissions."""

    @staticmethod
    def role_has_permission(role: Role, permission: Permission) -> bool:
        """Check if a role includes a specific permission."""
        return permission in ROLE_PERMISSIONS.get(role, set())

    @classmethod
    def evaluate_access(
        cls,
        context: TenantContext,
        target_tenant_id: TenantId,
        permission: Permission,
    ) -> tuple[bool, str]:
        """
        Evaluate if context is authorized to perform permission on target_tenant_id.
        Returns (is_allowed, reason).
        """
        principal = context.principal

        # 1. Platform Admin attempt to read/ingest tenant telemetry: Forbidden by architecture
        if principal.is_platform_scoped():
            if permission in (Permission.TELEMETRY_READ, Permission.TELEMETRY_INGEST, Permission.TELEMETRY_EXPORT):
                return (
                    False,
                    f"Platform roles ({principal.role.value}) are strictly prohibited from directly accessing tenant telemetry data.",
                )
            if cls.role_has_permission(principal.role, permission):
                return True, "Authorized by platform role policy."
            return False, f"Platform role '{principal.role.value}' lacks permission '{permission.value}'."

        # 2. Cross-tenant access check
        if context.tenant_id != target_tenant_id:
            return (
                False,
                f"Cross-tenant access forbidden: Caller tenant '{context.tenant_id}' cannot access target tenant '{target_tenant_id}'.",
            )

        # 3. RBAC permission check within tenant boundary
        if not cls.role_has_permission(principal.role, permission):
            return (
                False,
                f"Principal '{principal.principal_id}' with role '{principal.role.value}' lacks permission '{permission.value}' in tenant '{context.tenant_id}'.",
            )

        return True, "Authorized by tenant RBAC policy."

    @classmethod
    def enforce_access(
        cls,
        context: TenantContext,
        target_tenant_id: TenantId,
        permission: Permission,
    ) -> None:
        """
        Enforce access policy, raising typed exceptions on violation.
        """
        principal = context.principal

        # Cross-tenant boundary check
        if not principal.is_platform_scoped() and context.tenant_id != target_tenant_id:
            raise CrossTenantAccessViolation(
                principal_id=principal.principal_id,
                caller_tenant_id=context.tenant_id,
                target_tenant_id=target_tenant_id,
                action=permission.value,
            )

        allowed, reason = cls.evaluate_access(context, target_tenant_id, permission)
        if not allowed:
            if not principal.is_platform_scoped() and context.tenant_id != target_tenant_id:
                raise CrossTenantAccessViolation(
                    principal_id=principal.principal_id,
                    caller_tenant_id=context.tenant_id,
                    target_tenant_id=target_tenant_id,
                    action=permission.value,
                )
            raise UnauthorizedError(
                principal_id=principal.principal_id,
                tenant_id=target_tenant_id,
                required_permission=permission.value,
            )
