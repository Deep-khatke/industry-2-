"""Tenancy and multi-tenant security package for Federated Cyber Shield."""

from .audit import AuditEvent, AuditLogger
from .context import SecurityPrincipal, TenantContext
from .exceptions import (
    CrossTenantAccessViolation,
    InactiveTenantError,
    TenancyError,
    TenantNotFoundError,
    UnauthorizedError,
    UntrustedTenantClaimViolation,
)
from .models import (
    ExporterRegistration,
    Permission,
    Role,
    TenantConfig,
    TenantId,
    TenantStatus,
)
from .policy import PolicyEngine
from .registry import TenantRegistry

__all__ = [
    "AuditEvent",
    "AuditLogger",
    "CrossTenantAccessViolation",
    "ExporterRegistration",
    "InactiveTenantError",
    "Permission",
    "PolicyEngine",
    "Role",
    "SecurityPrincipal",
    "TenancyError",
    "TenantConfig",
    "TenantContext",
    "TenantId",
    "TenantNotFoundError",
    "TenantRegistry",
    "TenantStatus",
    "UnauthorizedError",
    "UntrustedTenantClaimViolation",
]
