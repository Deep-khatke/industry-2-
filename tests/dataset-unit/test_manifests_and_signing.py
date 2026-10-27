from pathlib import Path

import pytest

from fcs_udip.manifests.builder import ManifestBuilder, ManifestVerificationError


@pytest.mark.dataset_unit
class TestManifestsAndSigning:
    """Validate DatasetManifest contract creation, HMAC signing, and tamper detection."""

    def test_build_sign_and_verify_manifest(self, tmp_path: Path) -> None:
        builder = ManifestBuilder(dev_secret_key=b"test-secret-key-12345")

        manifest = builder.build_dataset_manifest(
            dataset_id="NF-UQ-NIDS-v2-Test",
            dataset_version="2.0.0",
            source_lineage=["NF-UQ-NIDS-v2"],
            feature_schema_digest="a" * 64,
            label_taxonomy_digest="b" * 64,
            split_policy_digest="c" * 64,
            row_counts={"train": 1000, "val": 200, "test": 200},
            source_statistics={"clean_ratio": 1.0},
            output_artifact_digests={"train.parquet": "d" * 64},
            license_info={"license_type": "RESEARCH_ONLY"},
        )

        assert manifest.signature is not None
        assert manifest.signature.algorithm == "HMAC-SHA256"
        assert manifest.signature.is_production_authority is False

        manifest_file = tmp_path / "manifest.json"
        builder.save_manifest(manifest, manifest_file)

        # Verification should succeed
        verified = builder.load_and_verify(manifest_file)
        assert verified.dataset_id == "NF-UQ-NIDS-v2-Test"

    def test_tampered_manifest_fails_verification(self, tmp_path: Path) -> None:
        builder = ManifestBuilder(dev_secret_key=b"test-secret-key-12345")

        manifest = builder.build_dataset_manifest(
            dataset_id="NF-UQ-NIDS-v2-Test",
            dataset_version="2.0.0",
            source_lineage=["NF-UQ-NIDS-v2"],
            feature_schema_digest="a" * 64,
            label_taxonomy_digest="b" * 64,
            split_policy_digest="c" * 64,
            row_counts={"train": 1000, "val": 200, "test": 200},
            source_statistics={"clean_ratio": 1.0},
            output_artifact_digests={"train.parquet": "d" * 64},
            license_info={"license_type": "RESEARCH_ONLY"},
        )

        manifest_file = tmp_path / "tampered_manifest.json"
        builder.save_manifest(manifest, manifest_file)

        # Tamper with the row count in the saved JSON file
        content = manifest_file.read_text(encoding="utf-8")
        tampered_content = content.replace('"train": 1000', '"train": 999999')
        manifest_file.write_text(tampered_content, encoding="utf-8")

        # Loading tampered manifest must raise ManifestVerificationError
        with pytest.raises(ManifestVerificationError) as exc_info:
            builder.load_and_verify(manifest_file)
        assert "Signature verification FAILED" in str(exc_info.value)
