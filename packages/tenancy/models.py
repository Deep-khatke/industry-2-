"""Data models and enums for multi-tenant identity and authorization."""

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

TENANT_ID_PATTERN = r"^[a-z0-9][a-z0-9_-]{2,63}$"
TENANT_ID_REGEX = re.compile(TENANT_ID_PATTERN)

TenantId = Annotated[
    str,
    Field(
        min_length=3,
        max_length=64,
        pattern=TENANT_ID_PATTERN,
        description="Unique identifier for a tenant (alphanumeric, lowercase, hyphen, underscore)",
    ),
]


class TenantStatus(StrEnum):
    """Lifecycle status of an ISP tenant."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DECOMMISSIONED = "DECOMMISSIONED"


class Role(StrEnum):
    """Hierarchical role-based access control roles."""

    TENANT_ADMIN = "TENANT_ADMIN"
    TENANT_ANALYST = "TENANT_ANALYST"
    SECURITY_ANALYST = "SECURITY_ANALYST"
    SECURITY_RESPONDER = "SECURITY_RESPONDER"
    READ_ONLY = "READ_ONLY"
    TENANT_EXPORTER = "TENANT_EXPORTER"
    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    PLATFORM_AUDITOR = "PLATFORM_AUDITOR"


class Permission(StrEnum):
    """Granular permissions for data and control plane operations."""

    TELEMETRY_INGEST = "telemetry:ingest"
    TELEMETRY_READ = "telemetry:read"
    TELEMETRY_EXPORT = "telemetry:export"
    AUDIT_READ = "audit:read"
    AUDIT_WRITE = "audit:write"
    TENANT_MANAGE = "tenant:manage"
    POLICY_EVALUATE = "policy:evaluate"
    INCIDENT_READ = "incident:read"
    INCIDENT_WRITE = "incident:write"
    RESPONSE_READ = "response:read"
    RESPONSE_APPROVE = "response:approve"


class ExporterRegistration(BaseModel):
    """Configuration for an authorized network telemetry exporter (router/switch/probe)."""

    exporter_id: str = Field(..., min_length=3, max_length=64)
    ip_address: str = Field(..., description="IPv4 or IPv6 address of the exporter")
    observation_domain_id: int = Field(default=0, ge=0, le=4294967295)
    sample_rate: int = Field(default=1, ge=1, description="1-in-N flow sampling rate")
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("exporter_id")
    @classmethod
    def validate_exporter_id(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_\-\.:]{3,64}$", v):
            raise ValueError(f"Invalid exporter_id format: '{v}'")
        return v


class TenantConfig(BaseModel):
    """Configuration and registration boundary for an ISP tenant."""

    tenant_id: TenantId
    name: str = Field(..., min_length=2, max_length=128)
    region: str = Field(default="ap-south-1")
    status: TenantStatus = Field(default=TenantStatus.ACTIVE)
    allowed_cidr_blocks: list[str] = Field(default_factory=list)
    max_events_per_sec: int = Field(default=10000, ge=1)
    exporters: dict[str, ExporterRegistration] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def register_exporter(self, exporter: ExporterRegistration) -> None:
        """Register a new exporter to this tenant."""
        self.exporters[exporter.exporter_id] = exporter

    def is_exporter_authorized(self, ip_address: str, observation_domain_id: int) -> bool:
        """Check if an exporter IP and observation domain belong to this tenant."""
        if self.status != TenantStatus.ACTIVE:
            return False
        for exp in self.exporters.values():
            if exp.active and exp.ip_address == ip_address and exp.observation_domain_id == observation_domain_id:
                return True
        return False
