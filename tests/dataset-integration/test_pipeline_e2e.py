"""End-to-end integration tests for FCS-UDIP dataset intelligence pipeline."""

from pathlib import Path

import polars as pl
import pytest

from fcs_udip.deduplication.deduplicator import DatasetDeduplicator
from fcs_udip.exports.model_exporter import ModelDatasetExporter
from fcs_udip.harmonization.feature_harmonizer import FeatureHarmonizer
from fcs_udip.harmonization.label_normalizer import LabelNormalizer
from fcs_udip.manifests.builder import ManifestBuilder
from fcs_udip.partitions.federated_partitioner import FederatedPartitioner
from fcs_udip.preprocessing.preprocessor import TrainingOnlyPreprocessor
from fcs_udip.schemas.inspector import SchemaInspector
from fcs_udip.splitting.splitter import DatasetSplitter
from fcs_udip.validation.quality_validator import DataQualityValidator
from packages.contracts.feature_spec import get_research_feature_spec
from packages.contracts.partition_manifest import PartitionRegime


@pytest.mark.dataset_integration
class TestPipelineE2E:
    """Validate full autonomous pipeline workflow from raw telemetry fixture to signed handoff artifacts."""

    def test_full_pipeline_execution(self, tmp_path: Path) -> None:
        input_fixture = Path("data/synthetic-fixtures/sample_netflow_v2.parquet")
        assert input_fixture.exists()

        # 1. Schema Inspection
        inspector = SchemaInspector()
        inspection = inspector.inspect_file(input_fixture)
        assert inspection["is_netflow_v2_compatible"]
        assert inspection["canonical_features_matched_count"] == 43

        # 2. Quality Validation
        raw_df = pl.read_parquet(input_fixture)
        validator = DataQualityValidator()
        clean_df, quaran_df, qmetrics = validator.validate_and_clean(raw_df)
        assert qmetrics["clean_row_count"] == 1400

        # 3. Label Normalization & Harmonization
        normalizer = LabelNormalizer("configs/datasets/label_mapping.yaml")
        norm_df = normalizer.apply_normalization(clean_df, source_id="NF-UQ-NIDS-v2")
        harmonizer = FeatureHarmonizer()
        norm_df = harmonizer.standardize_column_names(norm_df)
        norm_df = harmonizer.apply_privacy_subnet_masking(norm_df)

        assert "SRC_PREFIX_MASKED" in norm_df.columns
        assert "canonical_attack_label" in norm_df.columns
        assert "binary_label" in norm_df.columns

        # 4. Deduplication
        dedup = DatasetDeduplicator()
        dedup_df, dstats = dedup.deduplicate(norm_df, mode="exact")
        assert dstats["retained_count"] == 1400

        # 5. Group-Aware Splitting
        splitter = DatasetSplitter(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=42)
        train_df, val_df, test_df, split_manifest = splitter.split_group_aware(dedup_df)
        assert len(train_df) + len(val_df) + len(test_df) == 1400

        # Zero train/test host overlap
        train_hosts = set(train_df["IPV4_SRC_ADDR"].to_list())
        test_hosts = set(test_df["IPV4_SRC_ADDR"].to_list())
        assert len(train_hosts.intersection(test_hosts)) == 0

        # 6. Training-Only Preprocessing
        pre = TrainingOnlyPreprocessor()
        pre.fit(train_df)
        train_prep = pre.transform(train_df)
        val_prep = pre.transform(val_df)
        test_prep = pre.transform(test_df)
        assert len(train_prep) == len(train_df)
        assert len(val_prep) == len(val_df)
        assert len(test_prep) == len(test_df)

        # 7. Model-Specific Exports
        exporter = ModelDatasetExporter(output_dir=tmp_path / "models")
        gen_df = exporter.export_general_ids(train_prep)
        ddos_df = exporter.export_ddos_specialist(train_prep)
        scan_df = exporter.export_scanning_specialist(train_prep)
        exporter.export_botnet_specialist(train_prep)
        benign_anom, mixed_eval = exporter.export_anomaly_detector_views(train_prep, test_prep)

        assert "binary_label" in gen_df.columns
        assert (benign_anom["binary_label"] == 0).all()  # Anomaly train is 100% benign!
        assert len(ddos_df) > 0
        assert len(scan_df) > 0

        # 8. Seven Simulated ISP Federated Partitions
        partitioner = FederatedPartitioner(client_count=7, seed=42)
        client_dfs, part_manifest = partitioner.partition(train_prep, regime=PartitionRegime.IID)
        assert len(client_dfs) == 7
        total_partitioned = sum(len(c) for c in client_dfs.values())
        assert total_partitioned == len(train_prep)

        # 9. Signed Dataset Manifest & Verification
        builder = ManifestBuilder()
        research_spec = get_research_feature_spec()
        manifest = builder.build_dataset_manifest(
            dataset_id="NF-UQ-NIDS-v2-E2E-Integration",
            dataset_version="2.0.0",
            source_lineage=["NF-UQ-NIDS-v2"],
            feature_schema_digest=research_spec.compute_schema_digest(),
            label_taxonomy_digest=split_manifest.compute_manifest_digest()[:32],
            split_policy_digest=split_manifest.compute_manifest_digest()[:32],
            row_counts={
                "raw": len(raw_df),
                "clean": len(clean_df),
                "train": len(train_prep),
                "val": len(val_prep),
                "test": len(test_prep),
            },
            source_statistics={"clean_ratio": 1.0},
            output_artifact_digests={"train.parquet": split_manifest.train_record_digest},
            license_info={"license_type": "RESEARCH_ONLY", "commercial_allowed": "false"},
        )
        manifest_file = tmp_path / "dataset_manifest.json"
        builder.save_manifest(manifest, manifest_file)

        # Verify manifest
        verified = builder.load_and_verify(manifest_file)
        assert verified.dataset_id == "NF-UQ-NIDS-v2-E2E-Integration"
