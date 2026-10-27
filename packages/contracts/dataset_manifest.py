"""DatasetManifest contract and development signing primitives for FCS-UDIP."""

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class SignatureMetadata(BaseModel):
    """Cryptographic development signature container."""

    algorithm: str = Field(default="HMAC-SHA256", description="Cryptographic signing algorithm")
    key_id: str = Field(default="dev-pipeline-ephemeral-v1", description="Development key identifier")
    signature_hex: str = Field(..., description="Hex-encoded signature over canonical manifest payload")
    signed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Signature generation timestamp in UTC",
    )
    is_production_authority: bool = Field(
        default=False,
        description="Must remain FALSE in Phase 2 dev environment. Production authority reserved for later phases.",
    )


class DatasetManifest(BaseModel):
    """
    Cryptographically verifiable data contract recording complete provenance,
    schema digests, row counts, and output hashes of processed datasets.
    """

    manifest_schema_version: str = Field(default="1.0.0", description="Manifest contract schema version")
    dataset_id: str = Field(..., description="Unique dataset identifier (e.g. nf-uq-nids-v2-preprocessed)")
    dataset_version: str = Field(..., description="Dataset release version (e.g. 2.0.0)")
    source_lineage: list[str] = Field(..., description="List of registered source IDs contributing to dataset")
    source_checksums: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of raw source files to SHA-256 checksums",
    )
    license_info: dict[str, str] = Field(
        default_factory=dict,
        description="License terms, research restrictions, citation, commercial status",
    )
    feature_schema_digest: str = Field(..., description="SHA-256 digest of ordered feature specification")
    label_taxonomy_digest: str = Field(..., description="SHA-256 digest of active label taxonomy mapping")
    split_policy_digest: str = Field(..., description="SHA-256 digest of active train/val/test split policy")
    preprocessing_version: str = Field(default="1.0.0", description="Version of preprocessing transforms")
    build_code_revision: str = Field(default="local-dev", description="Git commit hash or build version")
    creation_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of dataset build in UTC",
    )
    row_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Row counts per partition (raw, clean, train, val, test, quarantined)",
    )
    source_statistics: dict[str, Any] = Field(
        default_factory=dict,
        description="Breakdown of samples per source dataset and per attack category",
    )
    output_artifact_digests: dict[str, str] = Field(
        default_factory=dict,
        description="File path relative to data/processed to SHA-256 checksum",
    )
    signature: SignatureMetadata | None = Field(
        default=None,
        description="Cryptographic development signature verifying integrity",
    )

    def to_canonical_dict(self) -> dict[str, Any]:
        """Produce deterministic dictionary excluding signature for signing and hashing."""
        data = self.model_dump(mode="json")
        data.pop("signature", None)
        return data

    def to_canonical_json(self) -> str:
        """Deterministic JSON string representation with sorted keys."""
        return json.dumps(self.to_canonical_dict(), sort_keys=True)

    def compute_manifest_digest(self) -> str:
        """SHA-256 digest of canonical manifest payload."""
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()

    def sign(self, secret_key: bytes, key_id: str = "dev-pipeline-ephemeral-v1") -> "DatasetManifest":
        """Generate HMAC-SHA256 development signature over the manifest digest."""
        digest = self.compute_manifest_digest().encode("utf-8")
        sig_hex = hmac.new(secret_key, digest, hashlib.sha256).hexdigest()
        self.signature = SignatureMetadata(
            algorithm="HMAC-SHA256",
            key_id=key_id,
            signature_hex=sig_hex,
            signed_at=datetime.now(UTC),
            is_production_authority=False,
        )
        return self

    def verify_signature(self, secret_key: bytes) -> bool:
        """Verify the manifest signature against the given secret key."""
        if not self.signature:
            return False
        digest = self.compute_manifest_digest().encode("utf-8")
        expected_sig = hmac.new(secret_key, digest, hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.signature.signature_hex, expected_sig)
