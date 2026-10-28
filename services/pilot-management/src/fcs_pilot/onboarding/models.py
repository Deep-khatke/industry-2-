"""Data models for ISP Pilot onboarding and lifecycle state management."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field


class OnboardingStatus(StrEnum):
    """Permitted states in the ISP pilot onboarding lifecycle."""
    DRAFT = "DRAFT"
    AUTHORIZATION_PENDING = "AUTHORIZATION_PENDING"
    TECHNICAL_REVIEW = "TECHNICAL_REVIEW"
    SECURITY_REVIEW = "SECURITY_REVIEW"
    READY_FOR_SHADOW = "READY_FOR_SHADOW"
    SHADOW_ACTIVE = "SHADOW_ACTIVE"
    SHADOW_COMPLETED = "SHADOW_COMPLETED"
    PILOT_PAUSED = "PILOT_PAUSED"
    PILOT_BLOCKED = "PILOT_BLOCKED"
    PILOT_CLOSED = "PILOT_CLOSED"


class EnvironmentMode(StrEnum):
    """Phase 9 operational environment modes."""
    MODE_A_SYNTHETIC = "MODE_A_SYNTHETIC"
    MODE_B_REAL_SHADOW = "MODE_B_REAL_SHADOW"
    MODE_C_MANUAL_VALIDATION = "MODE_C_MANUAL_VALIDATION"


class ExporterConfig(BaseModel):
    """Configuration and capability metadata for an ISP router/firewall exporter."""
    exporter_id: str = Field(..., description="Unique exporter identifier")
    vendor: str = Field(..., description="Hardware/software vendor (e.g. Cisco, Juniper, MikroTik)")
    model: str = Field(..., description="Device model or software agent")
    protocol: str = Field(..., description="Export protocol: 'IPFIX' or 'NetFlow_v9'")
    ip_address: str = Field(..., description="Management or export source IP address")
    expected_frequency_sec: int = Field(default=15, description="Expected flow export interval in seconds")
    sampling_rate: int = Field(default=1, description="Packet sampling rate: 1-in-N (1 = un-sampled)")
    observation_domain_id: int = Field(default=1, description="IPFIX/NetFlow observation domain ID")
    firmware_version: str | None = Field(default=None, description="Router firmware version if available")
    active: bool = Field(default=True, description="Whether this exporter is active")


class NetworkScope(BaseModel):
    """Approved network boundaries for telemetry collection."""
    prefixes: list[str] = Field(default_factory=list, description="List of CIDR prefixes authorized for monitoring")
    observation_domain_ids: list[int] = Field(default_factory=list, description="Approved observation domains")


class AuthorizationRecord(BaseModel):
    """Legal and operational authorization record for real ISP integration."""
    authorization_status: str = Field(..., description="Current authorization status")
    written_agreement_ref: str | None = Field(default=None, description="Reference to signed legal agreement")
    approved_by: str | None = Field(default=None, description="Approving authority identity")
    approved_at: datetime | None = Field(default=None, description="Timestamp of formal authorization")
    change_window_schedule: str | None = Field(default=None, description="Approved maintenance window schedule")
    emergency_stop_contact: str | None = Field(default=None, description="24/7 emergency pause contact")
    zero_cost_verified: bool = Field(default=True, description="Confirmation that zero billable infrastructure is used")


class StateTransitionRecord(BaseModel):
    """Auditable log entry for state transitions."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    pilot_id: str
    tenant_id: str
    from_state: OnboardingStatus
    to_state: OnboardingStatus
    actor_id: str
    actor_role: str
    reason: str
    evidence_ref: str | None = None


class PilotProfile(BaseModel):
    """Comprehensive tenant-scoped ISP pilot configuration."""
    pilot_id: str = Field(..., description="Unique pilot identifier")
    tenant_id: str = Field(..., description="Associated tenant ID")
    isp_display_name: str = Field(..., description="Human-readable ISP name and ASN")
    environment_mode: EnvironmentMode = Field(default=EnvironmentMode.MODE_A_SYNTHETIC)
    status: OnboardingStatus = Field(default=OnboardingStatus.DRAFT)
    technical_contact: str = Field(..., description="Operational email or identifier")
    authorized_network_scope: NetworkScope = Field(default_factory=NetworkScope)
    exporters: list[ExporterConfig] = Field(default_factory=list)
    authorization: AuthorizationRecord | None = Field(default=None)
    data_retention_days: int = Field(default=7, description="Raw telemetry retention days")
    incident_retention_days: int = Field(default=90, description="Incident record retention days")
    blocker_reason: str | None = Field(default=None, description="Reason if status is PILOT_BLOCKED")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
