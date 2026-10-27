"""Manifest construction, serialization, development signing, and verification."""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from packages.contracts.dataset_manifest import DatasetManifest


class ManifestVerificationError(Exception):
    """Raised when manifest integrity or signature verification fails."""


class ManifestBuilder:
    """Constructs, serializes, and verifies tamper-evident DatasetManifest artifacts."""

    def __init__(self, dev_secret_key: bytes | None = None) -> None:
        # Default ephemeral development secret key for ₹0 local testing
        self.dev_secret_key = dev_secret_key or b"fcs-udip-ephemeral-dev-signing-key-phase2"

    def build_dataset_manifest(
        self,
        dataset_id: str,
        dataset_version: str,
        source_lineage: list[str],
        feature_schema_digest: str,
        label_taxonomy_digest: str,
        split_policy_digest: str,
        row_counts: dict[str, int],
        source_statistics: dict[str, Any],
        output_artifact_digests: dict[str, str],
        license_info: dict[str, str],
        preprocessing_version: str = "1.2.0",
        build_code_revision: str = "phase2-dev",
    ) -> DatasetManifest:
        """Construct and cryptographically sign a DatasetManifest."""
        manifest = DatasetManifest(
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            source_lineage=source_lineage,
            feature_schema_digest=feature_schema_digest,
            label_taxonomy_digest=label_taxonomy_digest,
            split_policy_digest=split_policy_digest,
            preprocessing_version=preprocessing_version,
            build_code_revision=build_code_revision,
            row_counts=row_counts,
            source_statistics=source_statistics,
            output_artifact_digests=output_artifact_digests,
            license_info=license_info,
        )
        # Sign with development HMAC-SHA256 key
        manifest.sign(self.dev_secret_key, key_id="dev-pipeline-ephemeral-v1")
        return manifest

    def save_manifest(self, manifest: DatasetManifest, output_path: Path | str) -> None:
        """Write signed manifest to disk formatted as deterministic JSON."""
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            f.write(manifest.model_dump_json(indent=2))

    def load_and_verify(self, manifest_path: Path | str) -> DatasetManifest:
        """
        Load manifest from disk and verify its cryptographic signature and schema integrity.
        Raises ManifestVerificationError if corrupt or signature is invalid.
        """
        p = Path(manifest_path)
        if not p.is_file():
            raise FileNotFoundError(f"Manifest file not found: {p}")

        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            manifest = DatasetManifest(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise ManifestVerificationError(f"Corrupted or schema-invalid manifest: {e}") from e

        if not manifest.signature:
            raise ManifestVerificationError("Manifest is unsigned (missing signature metadata).")

        is_valid = manifest.verify_signature(self.dev_secret_key)
        if not is_valid:
            raise ManifestVerificationError(
                f"Signature verification FAILED for manifest '{manifest.dataset_id}'. "
                f"Payload may have been altered or signed with an incompatible key."
            )

        return manifest
