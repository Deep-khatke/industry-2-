"""Security context and caller principal representation."""

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from .models import Role, TenantId


class SecurityPrincipal(BaseModel):
    """The identity and credentials of the entity performing an operation."""

    principal_id: str = Field(..., min_length=2, max_length=128)
    role: Role
    tenant_id: TenantId | None = Field(
        default=None,
        description="Tenant this principal belongs to. None for platform-level principals.",
    )
    metadata: dict[str, str] = Field(default_factory=dict)

    def is_platform_scoped(self) -> bool:
        """Return True if principal is a platform-level role."""
        return self.role in (Role.PLATFORM_ADMIN, Role.PLATFORM_AUDITOR)


class TenantContext(BaseModel):
    """Immutable execution context for a request or telemetry batch within a verified tenant boundary."""

    context_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    principal: SecurityPrincipal
    tenant_id: TenantId
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @classmethod
    def create_for_exporter(
        cls,
        tenant_id: TenantId,
        exporter_id: str,
        correlation_id: str | None = None,
    ) -> "TenantContext":
        """Create a trusted ingestion context for an authorized exporter."""
        principal = SecurityPrincipal(
            principal_id=f"exporter:{exporter_id}",
            role=Role.TENANT_EXPORTER,
            tenant_id=tenant_id,
            metadata={"exporter_id": exporter_id},
        )
        return cls(
            principal=principal,
            tenant_id=tenant_id,
            correlation_id=correlation_id or str(uuid.uuid4()),
        )

    @classmethod
    def create_for_user(
        cls,
        user_id: str,
        role: Role,
        tenant_id: TenantId,
        correlation_id: str | None = None,
    ) -> "TenantContext":
        """Create a verified context for an authenticated user."""
        principal = SecurityPrincipal(
            principal_id=user_id,
            role=role,
            tenant_id=tenant_id,
        )
        return cls(
            principal=principal,
            tenant_id=tenant_id,
            correlation_id=correlation_id or str(uuid.uuid4()),
        )
