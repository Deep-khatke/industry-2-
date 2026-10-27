"""
Cryptographic Manifest Contracts for Phase 7 Consortium Governance.
Implements RFC 8785 JSON Canonicalization (JCS), SHA-384 digests,
and Dual-Signature Envelopes (ECDSA P-256 + ML-DSA-65).
Architecture Version: 1.2.0 | Zero-Cost Invariant: ₹0 / $0
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
import rfc8785


class SignatureAlgorithm(str, Enum):
    """Approved signature algorithm identifiers."""
    ECDSA_P256_SHA384 = "ECDSA_P256_SHA384"
    ML_DSA_65 = "ML_DSA_65"  # NIST FIPS 204 Parameter Set


class CanonicalManifestBody(BaseModel):
    """
    The canonical inner payload of a Release Manifest.
    RFC 8785 canonicalization is applied strictly to this structure.
    Size is strictly constrained to <= 4096 bytes per Architecture v1.2.
    """
    release_id: str = Field(description="Globally unique release identifier (UUID4)")
    schema_version: str = Field(default="1.2.0", description="Contract schema version")
    manifest_sequence: int = Field(ge=1, description="Strictly monotonic manifest sequence number")
    artifact_type: str = Field(default="FCS_HMD_GENERAL_DETECTOR", description="Model artifact type")
    artifact_digest_sha384: str = Field(description="SHA-384 hexadecimal digest of model artifact")
    feature_schema_digest: str = Field(description="SHA-256 digest of 14 locked deployable features")
    tenant_or_federation_scope: str = Field(default="FEDERATED_COHORT_TIER1", description="Scope of deployment")
    model_lineage_reference: str = Field(description="Reference to base candidate manifest or parent release")
    evaluation_reference: str = Field(description="Hash or reference to verified evaluation report")
    policy_reference: str = Field(default="GOVERNANCE_POLICY_V1_2", description="Governing policy identifier")
    allowed_algorithms: List[str] = Field(
        default=["ECDSA_P256_SHA384", "ML_DSA_65"],
        description="Dual signature algorithm requirements"
    )
    validity_interval_start: str = Field(description="ISO 8601 start timestamp in UTC")
    validity_interval_end: str = Field(description="ISO 8601 expiration timestamp in UTC")

    def to_canonical_bytes(self) -> bytes:
        """Serialize inner manifest to canonical bytes conforming to RFC 8785 (JCS)."""
        data = self.model_dump()
        canonical_bytes = rfc8785.dumps(data)
        if len(canonical_bytes) > 4096:
            raise ValueError(
                f"Canonical manifest body exceeds 4096 byte contract limit: {len(canonical_bytes)} bytes"
            )
        return canonical_bytes

    def calculate_body_digest_sha384(self) -> str:
        """Calculate SHA-384 digest of the canonical body."""
        return hashlib.sha384(self.to_canonical_bytes()).hexdigest()


class SignatureBlock(BaseModel):
    """Cryptographic signature block containing algorithm, public key, and signature."""
    algorithm: SignatureAlgorithm
    key_id: str = Field(description="Identifier or fingerprint of signing key")
    public_key_hex: str = Field(description="Hex-encoded public key bytes")
    signature_hex: str = Field(description="Hex-encoded cryptographic signature")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DualSignedReleaseManifest(BaseModel):
    """
    Outer container holding canonical manifest body and dual signatures.
    Outer envelope remains outside the canonical signed bytes.
    Both ECDSA and ML-DSA-65 signatures MUST validate over identical canonical bytes.
    """
    body: CanonicalManifestBody
    conventional_signature: SignatureBlock = Field(
        description="ECDSA P-256 (SHA-384) signature block"
    )
    post_quantum_signature: SignatureBlock = Field(
        description="ML-DSA-65 (NIST FIPS 204) signature block"
    )
    consortium_endorsements: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Hyperledger Fabric 3-of-4 organization endorsement signatures"
    )
    ledger_commitment_reference: Optional[str] = Field(
        default=None,
        description="Fabric transaction ID committing this release to the ledger"
    )

    def get_canonical_bytes(self) -> bytes:
        """Returns the canonical bytes of the body that both signatures sign."""
        return self.body.to_canonical_bytes()
