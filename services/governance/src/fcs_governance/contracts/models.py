"""
Governance and Ledger Data Models for Phase 7 Consortium Governance.
Architecture Version: 1.2.0 | Zero-Cost Invariant: ₹0 / $0
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .state import ReleaseState


class GovernanceOrg(str, Enum):
    """The four consortium governing organizations defined by Architecture v1.2."""
    ISP_GOVERNANCE_A = "ISP_GOVERNANCE_A"
    ISP_GOVERNANCE_B = "ISP_GOVERNANCE_B"
    ISP_GOVERNANCE_C = "ISP_GOVERNANCE_C"
    PLATFORM_GOVERNANCE = "PLATFORM_GOVERNANCE"


class ApprovalRole(str, Enum):
    """Authorized reviewer roles."""
    REVIEWER_A = "REVIEWER_A"  # Primary security reviewer
    REVIEWER_B = "REVIEWER_B"  # Independent ML/privacy reviewer
    TENANT_ADMIN = "TENANT_ADMIN" # Tenant authorization for local activation


class ApprovalRecord(BaseModel):
    """Audit record for human or organizational release approvals."""
    approval_id: str
    release_id: str
    reviewer_identity: str
    reviewer_role: ApprovalRole
    governing_org: GovernanceOrg
    approved: bool
    comments: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    signature: Optional[str] = None


class EndorsementRecord(BaseModel):
    """Consortium peer endorsement record in Fabric."""
    endorser_msp_id: str
    org: GovernanceOrg
    endorser_cert_id: str
    endorsement_signature_hex: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ReleaseRecord(BaseModel):
    """Comprehensive release record tracked in registry and on-chain."""
    release_id: str
    manifest_digest_sha384: str
    artifact_digest_sha384: str
    evaluation_digest: str
    policy_version: str = "1.2.0"
    model_lineage_ref: str
    status: ReleaseState = ReleaseState.CANDIDATE
    approvals: List[ApprovalRecord] = Field(default_factory=list)
    endorsements: List[EndorsementRecord] = Field(default_factory=list)
    dual_signed_manifest: Optional[Dict[str, Any]] = None
    ledger_tx_id: Optional[str] = None
    committed_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RevocationReason(str, Enum):
    """Approved justification categories for model revocation."""
    VULNERABILITY_DISCOVERED = "VULNERABILITY_DISCOVERED"
    ACCURACY_DEGRADATION = "ACCURACY_DEGRADATION"
    CONSORTIUM_EMERGENCY_RECALL = "CONSORTIUM_EMERGENCY_RECALL"
    SIGNING_KEY_COMPROMISED = "SIGNING_KEY_COMPROMISED"
    SUPERSEDED_BY_ROLLBACK = "SUPERSEDED_BY_ROLLBACK"


class RevocationRecord(BaseModel):
    """Record of model or key revocation committed to ledger."""
    revocation_id: str
    target_release_id: str
    revoked_by_org: GovernanceOrg
    revoker_identity: str
    reason: RevocationReason
    details: str
    authorization_reference: str
    revocation_digest_sha384: str
    ledger_tx_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AuditBatchRecord(BaseModel):
    """Hiding Merkle commitment record for privacy-preserving audit batches."""
    batch_id: str
    scope: str = "FEDERATED_INCIDENT_AUDIT"
    merkle_root_hex: str
    leaf_count: int
    random_salt_hex: str
    domain_separator: str = "FCS_AUDIT_MERKLE_V1"
    ledger_tx_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OutboxStatus(str, Enum):
    """Status of outbox events awaiting ledger commitment."""
    PENDING = "PENDING"
    COMMITTED = "COMMITTED"
    FAILED = "FAILED"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


class OutboxEvent(BaseModel):
    """Durable outbox event record for ACID atomic domain actions."""
    event_id: str
    event_type: str  # "RELEASE_REGISTRATION", "REVOCATION", "AUDIT_COMMITMENT"
    aggregate_id: str # release_id, revocation_id, batch_id
    payload_json: str
    status: OutboxStatus = OutboxStatus.PENDING
    retry_count: int = 0
    max_retries: int = 5
    ledger_tx_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
