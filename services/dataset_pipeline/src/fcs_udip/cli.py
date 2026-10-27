"""Unified command-line interface orchestrator for FCS-UDIP."""

import argparse
import sys
from pathlib import Path
from typing import Any

import polars as pl

from packages.contracts.feature_spec import (
    get_research_feature_spec,
)
from packages.contracts.partition_manifest import PartitionRegime

from .acquisition.downloader import ControlledDatasetAcquisition
from .deduplication.deduplicator import DatasetDeduplicator
from .exports.model_exporter import ModelDatasetExporter
from .harmonization.feature_harmonizer import FeatureHarmonizer
from .harmonization.label_normalizer import LabelNormalizer
from .manifests.builder import ManifestBuilder
from .partitions.federated_partitioner import FederatedPartitioner
from .preprocessing.preprocessor import TrainingOnlyPreprocessor
from .registry.registry import DatasetRegistry
from .reports.parity_report import generate_feature_parity_report
from .reports.partition_report import generate_partition_report
from .reports.quality_report import generate_quality_report
from .schemas.inspector import SchemaInspector
from .splitting.splitter import DatasetSplitter
from .validation.quality_validator import DataQualityValidator


def build_parser() -> argparse.ArgumentParser:
    """Build root CLI parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="fcs-data",
        description="Federated Cyber Shield — Unified Dataset Intelligence Pipeline (FCS-UDIP)",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available pipeline subcommands")

    # sources
    sources_p = subparsers.add_parser("sources", help="Manage and inspect registered dataset sources")
    sources_sub = sources_p.add_subparsers(dest="sources_action")
    sources_sub.add_parser("list", help="List all registered sources")
    inspect_source_p = sources_sub.add_parser("inspect", help="Inspect single source metadata")
    inspect_source_p.add_argument("dataset_id", help="Dataset identifier (e.g. NF-UQ-NIDS-v2)")

    # licenses
    licenses_p = subparsers.add_parser("licenses", help="Audit dataset licensing terms and restrictions")
    licenses_sub = licenses_p.add_subparsers(dest="licenses_action")
    verify_p = licenses_sub.add_parser("verify", help="Verify licensing for intended use")
    verify_p.add_argument("dataset_id", help="Dataset identifier")
    verify_p.add_argument("--intended-use", default="RESEARCH", choices=["RESEARCH", "COMMERCIAL"])

    # download
    dl_p = subparsers.add_parser("download", help="Acquire dataset files with budget checks")
    dl_p.add_argument("dataset_id", help="Dataset identifier to acquire")
    dl_p.add_argument("--dry-run", action="store_true", default=True, help="Perform preflight evaluation without transfer")
    dl_p.add_argument("--max-bytes", type=int, default=1073741824, help="Maximum download budget in bytes")

    # inspect
    inspect_p = subparsers.add_parser("inspect", help="Inspect file schema and version compatibility")
    inspect_p.add_argument("file_path", help="Path to Parquet or CSV dataset file")

    # validate
    validate_p = subparsers.add_parser("validate", help="Run data quality checks and quarantine invalid rows")
    validate_p.add_argument("file_path", help="Path to input dataset file")
    validate_p.add_argument("--output-dir", default="data/staging", help="Output directory for clean and quarantine data")

    # normalize
    norm_p = subparsers.add_parser("normalize", help="Harmonize features and normalize attack taxonomy")
    norm_p.add_argument("file_path", help="Path to input dataset file")
    norm_p.add_argument("--source-id", default="NF-UQ-NIDS-v2", help="Originating dataset source identifier")
    norm_p.add_argument("--output", default="data/staging/normalized.parquet", help="Output file path")

    # deduplicate
    dedup_p = subparsers.add_parser("deduplicate", help="Detect duplicates and cross-source overlap")
    dedup_p.add_argument("file_path", help="Path to input dataset file")
    dedup_p.add_argument("--mode", default="exact", choices=["exact", "features_only"])
    dedup_p.add_argument("--output", default="data/staging/deduped.parquet", help="Output file path")

    # split
    split_p = subparsers.add_parser("split", help="Leakage-safe group-aware train/val/test splitting")
    split_p.add_argument("file_path", help="Path to clean dataset file")
    split_p.add_argument("--output-dir", default="data/processed/splits", help="Output directory for splits and manifest")
    split_p.add_argument("--seed", type=int, default=42, help="Deterministic random seed")

    # preprocess
    prep_p = subparsers.add_parser("preprocess", help="Training-only preprocessor fit and transform")
    prep_p.add_argument("train_path", help="Path to train split parquet")
    prep_p.add_argument("val_path", help="Path to val split parquet")
    prep_p.add_argument("test_path", help="Path to test split parquet")
    prep_p.add_argument("--output-dir", default="data/processed/preprocessed", help="Output directory")

    # export-general
    exp_gen_p = subparsers.add_parser("export-general", help="Export binary classification datasets")
    exp_gen_p.add_argument("file_path", help="Path to preprocessed parquet")
    exp_gen_p.add_argument("--output", default="data/processed/models/general_ids.parquet")

    # export-specialists
    exp_spec_p = subparsers.add_parser("export-specialists", help="Export specialist datasets (DDoS, Scanning, Botnet)")
    exp_spec_p.add_argument("file_path", help="Path to preprocessed parquet")
    exp_spec_p.add_argument("--output-dir", default="data/processed/models/specialists")

    # partition
    part_p = subparsers.add_parser("partition", help="Generate 7 simulated ISP federated partitions")
    part_p.add_argument("train_path", help="Path to preprocessed training parquet")
    part_p.add_argument("--clients", type=int, default=7, help="Number of simulated ISP clients")
    part_p.add_argument("--regime", default="IID", choices=["IID", "MODERATE_NON_IID", "STRONG_NON_IID"])
    part_p.add_argument("--output-dir", default="data/processed/partitions")

    # verify-manifest
    verify_m_p = subparsers.add_parser("verify-manifest", help="Verify signed DatasetManifest integrity")
    verify_m_p.add_argument("manifest_path", nargs="?", default=None, help="Path to signed dataset manifest JSON")
    verify_m_p.add_argument("--manifest", default=None, help="Path to signed dataset manifest JSON")

    # report
    report_p = subparsers.add_parser("report", help="Generate pipeline reports (quality, parity, partitions, G14)")
    report_p.add_argument("--output-dir", default="data/reports", help="Output directory for reports")

    # run
    run_p = subparsers.add_parser("run", help="Execute complete end-to-end pipeline")
    run_p.add_argument("--input", "--input-file", dest="input", default="data/synthetic-fixtures/sample_netflow_v2.parquet", help="Input file path")
    run_p.add_argument("--output-dir", default="data/processed", help="Root output directory")
    run_p.add_argument("--seed", type=int, default=42, help="Random seed")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point function returning exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return 0

    sources_yaml = Path("configs/datasets/sources.yaml")
    labels_yaml = Path("configs/datasets/label_mapping.yaml")
    registry = DatasetRegistry(sources_yaml if sources_yaml.exists() else None)

    try:
        if args.subcommand == "sources":
            if args.sources_action == "list":
                print("\nRegistered Cybersecurity Datasets (FCS-UDIP):")
                print("-" * 75)
                for s in registry.list_sources():
                    comm = "Commercial Permitted" if s.commercial_use_allowed else "RESEARCH ONLY"
                    print(f"• {s.dataset_id:<22} v{s.version:<6} [{comm}] - {s.publisher}")
                print("-" * 75)
                return 0

            elif args.sources_action == "inspect":
                source = registry.get_source(args.dataset_id)
                print(f"\nDataset Source: {source.dataset_id}")
                print(f"Version:        {source.version}")
                print(f"Publisher:      {source.publisher}")
                print(f"Authors:        {source.authors}")
                print(f"License Type:   {source.license_type}")
                print(f"Commercial:     {'YES' if source.commercial_use_allowed else 'NO (STRICTLY PROHIBITED)'}")
                print(f"Features:       {source.feature_count} ({source.feature_family})")
                print(f"Official URL:   {source.official_url}")
                print(f"Citation:       {source.citation}")
                print(f"Parent Sources: {', '.join(source.parent_sources) or 'None'}")
                return 0

        elif args.subcommand == "licenses":
            target_id = getattr(args, "dataset_id", None)
            intended = getattr(args, "intended_use", "RESEARCH")
            if not target_id:
                print("Error: Specify dataset_id to verify.")
                return 1
            res = registry.verify_licensing(target_id, intended_use=intended)
            print(f"\nLicensing Audit Result for '{target_id}':")
            print(f"Intended Use:       {res['intended_use']}")
            print(f"Status:             {res['status']}")
            print(f"License Type:       {res['license_type']}")
            print(f"Commercial Allowed: {res['commercial_allowed']}")
            print(f"Citation Required:  {res['citation_required']}")
            return 0

        elif args.subcommand == "download":
            source = registry.get_source(args.dataset_id)
            acq = ControlledDatasetAcquisition(max_download_bytes=args.max_bytes)
            # Simulated declared size of 12 GiB for full NF-UQ-NIDS-v2 or 50 MB for sample
            simulated_size = 12 * 1024**3 if "NF-UQ-NIDS-v2" in args.dataset_id else 50 * 1024**2
            res = acq.simulate_acquisition_plan(source.dataset_id, source.official_url, declared_size_bytes=simulated_size)
            print(f"\nControlled Acquisition Preflight for '{args.dataset_id}':")
            print(f"Declared Size:       {res['declared_size_mb']:.2f} MB")
            print(f"Download Budget Cap: {res['max_download_budget_mb']:.2f} MB")
            print(f"Within Budget:       {res['within_bandwidth_budget']}")
            print(f"Disk Free:           {res['disk_preflight']['free_gb']} GB")
            print(f"Recommendation:      {res['recommendation']}")
            return 0

        elif args.subcommand == "inspect":
            inspector = SchemaInspector()
            info = inspector.inspect_file(args.file_path)
            print(f"\nDataset Schema Inspection: {args.file_path}")
            print(f"Detected Classification:   {info['detected_classification']}")
            print(f"Total Columns:             {info['total_columns']}")
            print(f"Canonical Matched (43):    {info['canonical_features_matched_count']} / 43")
            print(f"Missing Canonical:         {len(info['missing_canonical_features'])} features")
            print(f"Binary Label Present:      {info['has_binary_label']}")
            print(f"Attack Label Present:      {info['has_attack_label']}")
            print(f"NetFlow v2 Compatible:     {info['is_netflow_v2_compatible']}")
            return 0

        elif args.subcommand == "validate":
            p = Path(args.file_path)
            df = pl.read_parquet(p) if p.suffix == ".parquet" else pl.read_csv(p)
            validator = DataQualityValidator()
            clean_df, quaran_df, metrics = validator.validate_and_clean(df)
            out_dir = Path(args.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            clean_df.write_parquet(out_dir / "clean.parquet")
            quaran_df.write_parquet(out_dir / "quarantine.parquet")
            print("\nQuality Validation Complete:")
            print(f"Clean Records:       {metrics['clean_row_count']:,} ({metrics['clean_ratio']*100:.2f}%)")
            print(f"Quarantined Records: {metrics['quarantine_row_count']:,}")
            print(f"Artifacts written to: {out_dir}")
            return 0

        elif args.subcommand == "normalize":
            p = Path(args.file_path)
            df = pl.read_parquet(p) if p.suffix == ".parquet" else pl.read_csv(p)
            normalizer = LabelNormalizer(labels_yaml if labels_yaml.exists() else None)
            norm_df = normalizer.apply_normalization(df, source_id=args.source_id)
            harmonizer = FeatureHarmonizer()
            norm_df = harmonizer.standardize_column_names(norm_df)
            norm_df = harmonizer.apply_privacy_subnet_masking(norm_df)
            out_p = Path(args.output)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            norm_df.write_parquet(out_p)
            print(f"Normalized dataset written to: {out_p} ({len(norm_df):,} rows)")
            return 0

        elif args.subcommand == "deduplicate":
            p = Path(args.file_path)
            df = pl.read_parquet(p) if p.suffix == ".parquet" else pl.read_csv(p)
            dedup = DatasetDeduplicator()
            dedup_df, stats = dedup.deduplicate(df, mode=args.mode)
            out_p = Path(args.output)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            dedup_df.write_parquet(out_p)
            print(f"\nDeduplication ({args.mode}) Complete:")
            print(f"Initial: {stats['initial_count']:,} | Retained: {stats['retained_count']:,} | Dropped: {stats['duplicates_removed']:,}")
            return 0

        elif args.subcommand == "split":
            p = Path(args.file_path)
            df = pl.read_parquet(p) if p.suffix == ".parquet" else pl.read_csv(p)
            splitter = DatasetSplitter(seed=args.seed)
            train_df, val_df, test_df, manifest = splitter.split_group_aware(df)
            out_dir = Path(args.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            train_df.write_parquet(out_dir / "train.parquet")
            val_df.write_parquet(out_dir / "val.parquet")
            test_df.write_parquet(out_dir / "test.parquet")
            with (out_dir / "split_manifest.json").open("w", encoding="utf-8") as f:
                f.write(manifest.to_canonical_json())
            print(f"\nGroup-Aware Splitting Complete (Seed {args.seed}):")
            print(f"Train: {len(train_df):,} | Val: {len(val_df):,} | Test: {len(test_df):,}")
            print(f"Manifest written to: {out_dir / 'split_manifest.json'}")
            return 0

        elif args.subcommand == "preprocess":
            train_df = pl.read_parquet(args.train_path)
            val_df = pl.read_parquet(args.val_path)
            test_df = pl.read_parquet(args.test_path)
            preprocessor = TrainingOnlyPreprocessor()
            # Strictly fit on train ONLY
            preprocessor.fit(train_df)
            train_prep = preprocessor.transform(train_df)
            val_prep = preprocessor.transform(val_df)
            test_prep = preprocessor.transform(test_df)
            out_dir = Path(args.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            train_prep.write_parquet(out_dir / "train_preprocessed.parquet")
            val_prep.write_parquet(out_dir / "val_preprocessed.parquet")
            test_prep.write_parquet(out_dir / "test_preprocessed.parquet")
            preprocessor.save_state(out_dir / "preprocessor_state.json")
            print("\nTraining-Only Preprocessing Complete:")
            print(f"Parameters fit strictly on training set. Artifacts written to: {out_dir}")
            return 0

        elif args.subcommand == "export-general":
            df = pl.read_parquet(args.file_path)
            exporter = ModelDatasetExporter()
            gen_df = exporter.export_general_ids(df)
            out_p = Path(args.output)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            gen_df.write_parquet(out_p)
            print(f"General binary IDS dataset exported to: {out_p} ({len(gen_df):,} records)")
            return 0

        elif args.subcommand == "export-specialists":
            df = pl.read_parquet(args.file_path)
            exporter = ModelDatasetExporter(output_dir=args.output_dir)
            ddos_df = exporter.export_ddos_specialist(df)
            scan_df = exporter.export_scanning_specialist(df)
            bot_df = exporter.export_botnet_specialist(df)
            out_dir = Path(args.output_dir)
            ddos_df.write_parquet(out_dir / "ddos_specialist.parquet")
            scan_df.write_parquet(out_dir / "scanning_specialist.parquet")
            bot_df.write_parquet(out_dir / "botnet_specialist.parquet")
            print(f"\nSpecialist Datasets Exported to: {out_dir}")
            print(f"DDoS: {len(ddos_df):,} | Scanning: {len(scan_df):,} | Botnet: {len(bot_df):,}")
            return 0

        elif args.subcommand == "partition":
            train_df = pl.read_parquet(args.train_path)
            regime = PartitionRegime(args.regime)
            partitioner = FederatedPartitioner(client_count=args.clients)
            client_dfs, part_manifest = partitioner.partition(train_df, regime=regime)
            out_dir = Path(args.output_dir) / regime.value.lower()
            out_dir.mkdir(parents=True, exist_ok=True)
            for cid, cdf in client_dfs.items():
                cdf.write_parquet(out_dir / f"{cid}.parquet")
            with (out_dir / "partition_manifest.json").open("w", encoding="utf-8") as f:
                f.write(part_manifest.to_canonical_json())
            print(f"\nSeven ISP Federated Partitioning ({regime.value}) Complete:")
            for cid, cdf in client_dfs.items():
                print(f"  • {cid} ({part_manifest.client_partitions[cid].tenant_id_mapping}): {len(cdf):,} records")
            print(f"Partitions written to: {out_dir}")
            return 0

        elif args.subcommand == "verify-manifest":
            manifest_file = args.manifest or args.manifest_path
            if not manifest_file:
                print("Error: Specify manifest file path via positional argument or --manifest")
                return 1
            builder = ManifestBuilder()
            loaded_manifest = builder.load_and_verify(manifest_file)
            print("\nManifest Verification: SUCCESS")
            print(f"Dataset ID:         {loaded_manifest.dataset_id}")
            print(f"Version:            {loaded_manifest.dataset_version}")
            print(f"Signer Key ID:      {loaded_manifest.signature.key_id if loaded_manifest.signature else 'None'}")
            print(f"Algorithm:          {loaded_manifest.signature.algorithm if loaded_manifest.signature else 'None'}")
            print(f"Production Status:  {'PROD' if loaded_manifest.signature and loaded_manifest.signature.is_production_authority else 'DEVELOPMENT'}")
            return 0

        elif args.subcommand == "report":
            out_dir = Path(args.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            generate_feature_parity_report(out_dir / "feature_parity_report.md")
            print(f"Feature parity report generated at: {out_dir / 'feature_parity_report.md'}")
            return 0

        elif args.subcommand == "run":
            print("\n========================================================")
            print("FEDERATED CYBER SHIELD — PHASE 2 PIPELINE EXECUTION")
            print("========================================================")
            inp_path = Path(args.input)
            if not inp_path.exists():
                print(f"Input dataset not found: {inp_path}")
                return 1

            # 1. Inspect
            print("\n[STEP 1/9] Inspecting Schema...")
            inspector = SchemaInspector()
            info = inspector.inspect_file(inp_path)
            print(f"Columns: {info['total_columns']} | NetFlow v2 Matched: {info['canonical_features_matched_count']} / 43")

            # 2. Quality Validation & Quarantine
            print("\n[STEP 2/9] Executing Quality Rules & Quarantine...")
            raw_df = pl.read_parquet(inp_path) if inp_path.suffix == ".parquet" else pl.read_csv(inp_path)
            validator = DataQualityValidator()
            clean_df, quaran_df, qmetrics = validator.validate_and_clean(raw_df)
            print(f"Accepted Clean: {qmetrics['clean_row_count']:,} | Quarantined: {qmetrics['quarantine_row_count']:,}")

            # 3. Label Normalization & Harmonization
            print("\n[STEP 3/9] Harmonizing Features and Label Taxonomy...")
            normalizer = LabelNormalizer(labels_yaml if labels_yaml.exists() else None)
            norm_df = normalizer.apply_normalization(clean_df, source_id="NF-UQ-NIDS-v2")
            harmonizer = FeatureHarmonizer()
            norm_df = harmonizer.standardize_column_names(norm_df)
            norm_df = harmonizer.apply_privacy_subnet_masking(norm_df)

            # 4. Deduplication
            print("\n[STEP 4/9] Deduplicating Records...")
            dedup = DatasetDeduplicator()
            dedup_df, dstats = dedup.deduplicate(norm_df, mode="exact")
            print(f"Unique Retained: {dstats['retained_count']:,} (Dropped {dstats['duplicates_removed']:,} duplicates)")

            # 5. Leakage-Safe Splitting
            print("\n[STEP 5/9] Splitting into Train / Val / Test (Group-Aware)...")
            splitter = DatasetSplitter(seed=args.seed)
            train_df, val_df, test_df, split_manifest = splitter.split_group_aware(dedup_df)
            print(f"Train: {len(train_df):,} | Val: {len(val_df):,} | Test: {len(test_df):,}")

            # 6. Training-Only Preprocessing
            print("\n[STEP 6/9] Fitting Training-Only Preprocessing...")
            preprocessor = TrainingOnlyPreprocessor()
            preprocessor.fit(train_df)
            train_prep = preprocessor.transform(train_df)
            val_prep = preprocessor.transform(val_df)
            test_prep = preprocessor.transform(test_df)

            # Write processed data
            out_root = Path(args.output_dir)
            out_root.mkdir(parents=True, exist_ok=True)
            splits_dir = out_root / "splits"
            splits_dir.mkdir(parents=True, exist_ok=True)
            train_prep.write_parquet(splits_dir / "train.parquet")
            val_prep.write_parquet(splits_dir / "val.parquet")
            test_prep.write_parquet(splits_dir / "test.parquet")
            preprocessor.save_state(out_root / "preprocessor_state.json")

            # 7. Model-Specific Exports
            print("\n[STEP 7/9] Generating Model-Specific Dataset Views...")
            exporter = ModelDatasetExporter(output_dir=out_root / "models")
            gen_df = exporter.export_general_ids(train_prep)
            ddos_df = exporter.export_ddos_specialist(train_prep)
            scan_df = exporter.export_scanning_specialist(train_prep)
            bot_df = exporter.export_botnet_specialist(train_prep)
            benign_anom, _ = exporter.export_anomaly_detector_views(train_prep, test_prep)

            models_dir = out_root / "models"
            models_dir.mkdir(parents=True, exist_ok=True)
            gen_df.write_parquet(models_dir / "general_ids_train.parquet")
            ddos_df.write_parquet(models_dir / "ddos_specialist_train.parquet")
            scan_df.write_parquet(models_dir / "scanning_specialist_train.parquet")
            bot_df.write_parquet(models_dir / "botnet_specialist_train.parquet")
            benign_anom.write_parquet(models_dir / "benign_anomaly_train.parquet")

            # 8. Seven Simulated ISP Federated Partitions
            print("\n[STEP 8/9] Generating Seven Simulated ISP Federated Partitions...")
            part_dir = out_root / "partitions"
            part_manifests: dict[str, Any] = {}
            for regime in [PartitionRegime.IID, PartitionRegime.MODERATE_NON_IID, PartitionRegime.STRONG_NON_IID]:
                partitioner = FederatedPartitioner(client_count=7, seed=args.seed)
                client_dfs, pmanifest = partitioner.partition(train_prep, regime=regime)
                r_dir = part_dir / regime.value.lower()
                r_dir.mkdir(parents=True, exist_ok=True)
                for cid, cdf in client_dfs.items():
                    cdf.write_parquet(r_dir / f"{cid}.parquet")
                with (r_dir / "partition_manifest.json").open("w", encoding="utf-8") as f:
                    f.write(pmanifest.to_canonical_json())
                part_manifests[regime.value] = pmanifest

            # 9. Signed Manifest and Quality Reports
            print("\n[STEP 9/9] Generating Signed Dataset Manifest & Audit Reports...")
            builder = ManifestBuilder()
            research_spec = get_research_feature_spec()
            ds_manifest = builder.build_dataset_manifest(
                dataset_id="NF-UQ-NIDS-v2-FCS-Processed",
                dataset_version="2.0.0",
                source_lineage=["NF-UQ-NIDS-v2", "NF-UNSW-NB15-v2", "NF-CSE-CIC-IDS2018-v2", "NF-BoT-IoT-v2", "NF-ToN-IoT-v2"],
                feature_schema_digest=research_spec.compute_schema_digest(),
                label_taxonomy_digest=split_manifest.compute_manifest_digest()[:32],
                split_policy_digest=split_manifest.compute_manifest_digest()[:32],
                row_counts={
                    "raw": len(raw_df),
                    "clean": len(clean_df),
                    "quarantined": len(quaran_df),
                    "train": len(train_prep),
                    "val": len(val_prep),
                    "test": len(test_prep),
                },
                source_statistics={
                    "clean_ratio": qmetrics["clean_ratio"],
                    "duplicates_dropped": dstats["duplicates_removed"],
                },
                output_artifact_digests={
                    "train.parquet": split_manifest.train_record_digest,
                    "val.parquet": split_manifest.val_record_digest,
                    "test.parquet": split_manifest.test_record_digest,
                },
                license_info={
                    "license_type": "RESEARCH_ONLY",
                    "commercial_allowed": "false",
                    "citation": "Sarhan et al. 2022",
                },
            )
            manifest_path = out_root / "dataset_manifest.json"
            builder.save_manifest(ds_manifest, manifest_path)
            manifest_top = Path("data/manifests/dataset_manifest_v1.json")
            manifest_top.parent.mkdir(parents=True, exist_ok=True)
            builder.save_manifest(ds_manifest, manifest_top)

            # Generate Reports
            rep_dir = Path("data/reports")
            rep_dir.mkdir(parents=True, exist_ok=True)
            generate_quality_report("NF-UQ-NIDS-v2", qmetrics, rep_dir / "data_quality_report.md")
            generate_feature_parity_report(rep_dir / "feature_parity_report.md")
            generate_partition_report(part_manifests["IID"], rep_dir / "partition_report_iid.md")
            generate_partition_report(part_manifests["STRONG_NON_IID"], rep_dir / "partition_report_strong_non_iid.md")

            print("\n========================================================")
            print("PIPELINE EXECUTION COMPLETE (₹0 SPENT)")
            print(f"Dataset Manifest:  {manifest_path}")
            print(f"Splits Generated:  {splits_dir}")
            print(f"Model Exports:     {models_dir}")
            print(f"Federated Partitions: {part_dir}")
            print(f"Reports Directory: {rep_dir}")
            print("========================================================\n")
            return 0

    except Exception as e:
        print(f"\n[FCS-DATA ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
