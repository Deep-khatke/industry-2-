"""Unified CLI for FCS Phase 3 Machine Learning Model Development & Benchmarking."""

import argparse
import sys

from fcs_ml.data.loader import DatasetLoader
from fcs_ml.experiments.comparator import ModelComparator
from fcs_ml.experiments.runner import ExperimentSuiteRunner
from fcs_ml.experiments.tracker import ExperimentTracker
from fcs_ml.export.exporter import ModelExporter
from fcs_ml.features.selector import FeatureSelector, FeatureTrack
from fcs_ml.inference.engine import InferenceEngine
from fcs_ml.registry.registry import CandidateModelRegistry
from fcs_ml.training.trainer import ModelTrainer


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for fcs-ml CLI."""
    parser = argparse.ArgumentParser(
        prog="fcs-ml",
        description="Federated Cyber Shield — Phase 3 Machine Learning CLI (FCS v1.2)",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Phase 3 subcommands")

    # inspect-data
    subparsers.add_parser("inspect-data", help="Inspect dataset splits, columns, and class balance")

    # verify-data
    verify_p = subparsers.add_parser("verify-data", help="Verify dataset manifest and split integrity")
    verify_p.add_argument("--manifest", default="data/processed/dataset_manifest.json")

    # train
    train_p = subparsers.add_parser("train", help="Train a candidate model")
    train_p.add_argument("--model", required=True, choices=["baseline", "logistic", "lightgbm", "mlp", "multiclass"])
    train_p.add_argument("--track", default="research", choices=["research", "deployable"])
    train_p.add_argument("--max-train-rows", type=int, default=None)

    # evaluate
    eval_p = subparsers.add_parser("evaluate", help="Evaluate a candidate model against test split")
    eval_p.add_argument("--model-id", required=True)

    # compare
    comp_p = subparsers.add_parser("compare", help="Compare candidate models and generate benchmark tables")
    comp_p.add_argument("--output-md", default="artifacts/metrics/model_comparison.md")
    comp_p.add_argument("--output-csv", default="artifacts/metrics/model_comparison.csv")

    # benchmark
    bench_p = subparsers.add_parser("benchmark", help="Measure CPU inference latency and throughput")
    bench_p.add_argument("--model-id", default=None)

    # export
    exp_p = subparsers.add_parser("export", help="Export a candidate model artifact and manifest")
    exp_p.add_argument("--model-id", required=True)
    exp_p.add_argument("--output-dir", default="artifacts/candidate-models")

    # verify-artifact
    ver_p = subparsers.add_parser("verify-artifact", help="Verify integrity of registered model artifact")
    ver_p.add_argument("--model-id", required=True)

    # predict
    pred_p = subparsers.add_parser("predict", help="Execute inference on a sample flow record")
    pred_p.add_argument("--model-id", default="lightgbm_research_benchmark")

    # experiments
    exp_sub = subparsers.add_parser("experiments", help="List logged experiment runs")
    exp_sub.add_argument("action", nargs="?", default="list", choices=["list", "report"])

    # run-all
    run_all_p = subparsers.add_parser("run-all", help="Execute the complete Phase 3 benchmark suite (E3-01 to E3-09)")
    run_all_p.add_argument("--seed", type=int, default=42)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point returning integer exit status."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return 0

    loader = DatasetLoader()
    registry = CandidateModelRegistry()
    tracker = ExperimentTracker()

    try:
        if args.subcommand == "inspect-data":
            train_df, val_df, test_df = loader.load_splits()
            print("\n========================================================")
            print("FEDERATED CYBER SHIELD — DATASET SPLIT INSPECTION")
            print("========================================================")
            print(f"Training Split:   {train_df.shape[0]:,} rows x {train_df.shape[1]} columns")
            print(f"Validation Split: {val_df.shape[0]:,} rows x {val_df.shape[1]} columns")
            print(f"Test Split:       {test_df.shape[0]:,} rows x {test_df.shape[1]} columns")
            if "canonical_attack_label" in train_df.columns:
                print("\nTraining Attack Class Balance:")
                for row in train_df["canonical_attack_label"].value_counts().iter_rows():
                    print(f"  • {row[0]:<20}: {row[1]:,} flows")
            return 0

        elif args.subcommand == "verify-data":
            info = loader.verify_manifest(args.manifest)
            print("\nDataset Manifest Verification: SUCCESS")
            print(f"Dataset ID:             {info['dataset_id']}")
            print(f"Version:                {info['version']}")
            print(f"Signature Valid:        {info['signature_valid']}")
            print(f"Feature Schema Digest:  {info['feature_schema_digest'][:16]}...")
            print("Artifact Files on Disk:")
            for art, found in info["artifacts_found"].items():
                print(f"  • {art:<20}: {'FOUND' if found else 'MISSING'}")
            return 0

        elif args.subcommand == "train":
            track = FeatureTrack.RESEARCH_BENCHMARK if args.track == "research" else FeatureTrack.DEPLOYABLE_SUBSET
            train_df, val_df, test_df = loader.load_splits(max_train_rows=args.max_train_rows)
            selector = FeatureSelector(track=track)

            X_train, y_train, y_train_m, f_names = selector.extract_matrices(train_df)
            X_val, y_val, y_val_m, _ = selector.extract_matrices(val_df, f_names)
            X_test, y_test, y_test_m, _ = selector.extract_matrices(test_df, f_names)

            trainer = ModelTrainer(registry=registry)
            y_t_train = y_train_m if args.model == "multiclass" else y_train
            y_t_val = y_val_m if args.model == "multiclass" else y_val
            y_t_test = y_test_m if args.model == "multiclass" else y_test

            print(f"\nTraining model '{args.model}' under track '{track.value}' ({len(f_names)} features)...")
            model, manifest, metrics = trainer.train_and_evaluate(
                model_family=args.model,
                X_train=X_train,
                y_train=y_t_train,
                X_val=X_val,
                y_val=y_t_val,
                X_test=X_test,
                y_test=y_t_test,
                feature_names=f_names,
                track=track,
            )
            print("\nModel Training Complete & Registered:")
            print(f"Model ID:        {manifest.model_id}")
            print(f"Validation Thresh: {manifest.validation_threshold:.4f}")
            if "f1" in metrics:
                print(f"Test F1 Score:   {metrics['f1']:.4f}")
                print(f"Test PR-AUC:     {metrics['pr_auc']:.4f}")
                print(f"Test FPR:        {metrics['fpr']:.4f}")
            elif "macro_f1" in metrics:
                print(f"Macro F1:        {metrics['macro_f1']:.4f}")
            return 0

        elif args.subcommand == "evaluate":
            model, manifest = registry.load_model(args.model_id)
            track = FeatureTrack(manifest.feature_track)
            selector = FeatureSelector(track=track)
            _, _, test_df = loader.load_splits()
            X_test, y_test, y_test_m, _ = selector.extract_matrices(test_df, manifest.feature_names)

            y_eval = y_test_m if manifest.model_family == "MulticlassAttackClassifier" else y_test
            proba = model.predict_proba(X_test)

            print(f"\nEvaluation Results for '{args.model_id}':")
            if manifest.model_family != "MulticlassAttackClassifier":
                from fcs_ml.evaluation.metrics import compute_binary_metrics
                metrics = compute_binary_metrics(y_eval, proba, threshold=manifest.validation_threshold)
                print(f"PR-AUC:             {metrics['pr_auc']:.4f}")
                print(f"ROC-AUC:            {metrics['roc_auc']:.4f}")
                print(f"F1 Score:           {metrics['f1']:.4f}")
                print(f"Precision:          {metrics['precision']:.4f}")
                print(f"Recall:             {metrics['recall']:.4f}")
                print(f"False Positive Rate:{metrics['fpr']:.4f}")
            return 0

        elif args.subcommand == "compare":
            runner = ExperimentSuiteRunner(loader=loader, tracker=tracker, registry=registry)
            results = runner.run_e3_03_algorithm_comparison()
            comparator = ModelComparator()
            md_table = comparator.generate_comparison_table(
                results,
                output_csv=args.output_csv,
                output_md=args.output_md,
            )
            print("\n========================================================")
            print("CANDIDATE MODEL COMPARISON (RESEARCH BENCHMARK)")
            print("========================================================\n")
            print(md_table)
            print(f"\nSaved comparison artifacts to: {args.output_md} and {args.output_csv}")
            return 0

        elif args.subcommand == "benchmark":
            runner = ExperimentSuiteRunner(loader=loader, tracker=tracker, registry=registry)
            print("\nMeasuring CPU inference latency and throughput across batch sizes...")
            bench_res = runner.run_e3_08_resource_benchmark()
            print("\n| Model | Batch Size | p50 (ms) | p95 (ms) | p99 (ms) | Throughput (flows/s) |")
            print("| --- | --- | --- | --- | --- | --- |")
            for b in bench_res:
                print(f"| {b['model_family']} | {b['batch_size']} | {b['latency_p50_ms']:.3f} | {b['latency_p95_ms']:.3f} | {b['latency_p99_ms']:.3f} | {b['throughput_flows_per_sec']:.1f} |")
            return 0

        elif args.subcommand == "export":
            model, manifest = registry.load_model(args.model_id)
            res = ModelExporter.export_model(model, manifest, args.output_dir)
            print(f"\nModel exported successfully to: {res['export_directory']}")
            print(f"Bundle Checksum: {res['bundle_digest']}")
            return 0

        elif args.subcommand == "verify-artifact":
            res = registry.verify_model_artifact(args.model_id)
            print(f"\nArtifact Verification for '{args.model_id}':")
            print(f"Recorded SHA-256: {res['recorded_hash']}")
            print(f"Actual SHA-256:   {res['actual_hash']}")
            print(f"Status:           {'VERIFIED / VALID' if res['integrity_verified'] else 'FAILED'}")
            return 0 if res["integrity_verified"] else 1

        elif args.subcommand == "predict":
            engine = InferenceEngine(registry=registry)
            # Sample synthetic flow feature vector
            sample_record = {
                "L4_SRC_PORT": 443,
                "L4_DST_PORT": 52140,
                "PROTOCOL": 6,
                "L7_PROTO": 91,
                "IN_BYTES": 1500,
                "OUT_BYTES": 4500,
                "IN_PKTS": 10,
                "OUT_PKTS": 25,
                "FLOW_DURATION_MILLISECONDS": 450.0,
                "TCP_FLAGS": 27,
            }
            infer_res = engine.score_record(sample_record, model_id=args.model_id)
            print(f"\nInference Result for {args.model_id}:")
            print(f"Prediction:       {infer_res.predicted_label} (class {infer_res.prediction})")
            print(f"Probability:      {infer_res.calibrated_probability:.4f}")
            print(f"Threshold:        {infer_res.threshold_applied:.4f}")
            print(f"Uncertainty:      {'ABSTAIN' if infer_res.is_uncertain else 'CONFIDENT'}")
            print(f"Latency:          {infer_res.latency_microseconds:.2f} µs")
            print(f"Network Action:   {infer_res.network_action_executed} (Guaranteed False)")
            return 0

        elif args.subcommand == "experiments":
            runs = tracker.list_experiments()
            print(f"\nLogged Experiment Runs ({len(runs)} total):")
            print("-" * 75)
            for r in runs[:10]:
                m = r.get("metrics", {})
                f1_str = f"F1: {m.get('f1', 0.0):.4f}" if "f1" in m else ""
                exp_id = r.get("experiment_id") or r.get("phase") or "experiment"
                print(f"• {exp_id:<35} | {r.get('model_family', ''):<18} | {f1_str}")
            return 0

        elif args.subcommand == "run-all":
            print("\n========================================================")
            print("FEDERATED CYBER SHIELD — PHASE 3 COMPLETE BENCHMARK RUN")
            print("========================================================")
            runner = ExperimentSuiteRunner(loader=loader, tracker=tracker, registry=registry)

            print("\n[STEP 1/6] Running Algorithm Comparison (E3-03)...")
            e3_03_res = runner.run_e3_03_algorithm_comparison()

            print("\n[STEP 2/6] Running Feature Track Comparison (E3-04)...")
            runner.run_e3_04_track_comparison()

            print("\n[STEP 3/6] Running Cross-Source Generalization (E3-06)...")
            runner.run_e3_06_cross_source_generalization()

            print("\n[STEP 4/6] Measuring Inference Latency & Resource Benchmarks (E3-08)...")
            bench_res = runner.run_e3_08_resource_benchmark()

            print("\n[STEP 5/6] Running Robustness & Perturbation Tests (E3-09)...")
            runner.run_e3_09_robustness()

            print("\n[STEP 6/6] Generating Comparison Tables and Metrics Reports...")
            comparator = ModelComparator()
            comp_table = comparator.generate_comparison_table(
                e3_03_res,
                output_csv="artifacts/metrics/model_comparison.csv",
                output_md="artifacts/metrics/model_comparison.md",
            )
            print("\nBenchmark Suite Execution Complete!")
            print(comp_table)
            return 0

    except Exception as e:
        print(f"\n[FCS-ML ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
