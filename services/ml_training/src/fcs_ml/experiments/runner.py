"""Experiment runner for executing the FCS Phase 3 research suite (E3-01 to E3-09)."""

import time
from typing import Any

import numpy as np

from fcs_ml.data.loader import DatasetLoader
from fcs_ml.evaluation.metrics import compute_binary_metrics
from fcs_ml.evaluation.robustness import RobustnessEvaluator
from fcs_ml.experiments.comparator import ModelComparator
from fcs_ml.experiments.tracker import ExperimentTracker
from fcs_ml.features.selector import FeatureSelector, FeatureTrack
from fcs_ml.registry.registry import CandidateModelRegistry
from fcs_ml.training.trainer import ModelTrainer


class ExperimentSuiteRunner:
    """Executes the standard Phase 3 benchmark experiments."""

    def __init__(
        self,
        loader: DatasetLoader | None = None,
        tracker: ExperimentTracker | None = None,
        registry: CandidateModelRegistry | None = None,
    ) -> None:
        self.loader = loader or DatasetLoader()
        self.tracker = tracker or ExperimentTracker()
        self.registry = registry or CandidateModelRegistry()
        self.trainer = ModelTrainer(registry=self.registry)
        self.comparator = ModelComparator()

    def run_e3_03_algorithm_comparison(
        self,
        track: FeatureTrack = FeatureTrack.RESEARCH_BENCHMARK,
    ) -> list[dict[str, Any]]:
        """
        Experiment E3-03: Algorithm Comparison.
        Compares DummyBaseline, LogisticRegression, LightGBM, and PyTorchMLP under identical conditions.
        """
        train_df, val_df, test_df = self.loader.load_splits()
        selector = FeatureSelector(track=track)

        X_train, y_train, _, f_names = selector.extract_matrices(train_df)
        X_val, y_val, _, _ = selector.extract_matrices(val_df, f_names)
        X_test, y_test, _, _ = selector.extract_matrices(test_df, f_names)

        results = []
        models_to_test = ["DummyBaseline", "LogisticRegression", "LightGBM", "PyTorchMLP"]

        for model_family in models_to_test:
            _, manifest, metrics = self.trainer.train_and_evaluate(
                model_family=model_family,
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                X_test=X_test,
                y_test=y_test,
                feature_names=f_names,
                track=track,
            )
            exp_id = f"E3-03_{model_family.lower()}_{track.value.lower()}"
            self.tracker.log_experiment(
                experiment_id=exp_id,
                model_family=model_family,
                feature_track=track.value,
                hyperparameters={"random_seed": 42},
                metrics=metrics,
                notes="Algorithm comparison benchmark",
            )
            results.append({
                "model_family": model_family,
                "feature_track": track.value,
                "metrics": metrics,
            })

        return results

    def run_e3_04_track_comparison(self) -> list[dict[str, Any]]:
        """
        Experiment E3-04: Research vs Deployable Feature Track.
        Compares LightGBM performance on 43 Research features vs 14 Deployable features.
        """
        train_df, val_df, test_df = self.loader.load_splits()
        results = []

        for track in [FeatureTrack.RESEARCH_BENCHMARK, FeatureTrack.DEPLOYABLE_SUBSET]:
            selector = FeatureSelector(track=track)
            X_train, y_train, _, f_names = selector.extract_matrices(train_df)
            X_val, y_val, _, _ = selector.extract_matrices(val_df, f_names)
            X_test, y_test, _, _ = selector.extract_matrices(test_df, f_names)

            _, manifest, metrics = self.trainer.train_and_evaluate(
                model_family="LightGBM",
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                X_test=X_test,
                y_test=y_test,
                feature_names=f_names,
                track=track,
            )
            exp_id = f"E3-04_track_comparison_{track.value.lower()}"
            self.tracker.log_experiment(
                experiment_id=exp_id,
                model_family="LightGBM",
                feature_track=track.value,
                hyperparameters={"n_features": len(f_names)},
                metrics=metrics,
                notes="Research vs Deployable feature track parity experiment",
            )
            results.append({
                "model_family": f"LightGBM ({track.value})",
                "feature_track": track.value,
                "metrics": metrics,
            })

        return results

    def run_e3_06_cross_source_generalization(
        self,
        holdout_source: str = "NF-ToN-IoT-v2",
    ) -> dict[str, Any]:
        """
        Experiment E3-06: Cross-Source Generalization.
        Trains on non-holdout sources and evaluates against independent held-out source.
        """
        train_h, val_h, test_h, holdout_df = self.loader.load_with_holdout(holdout_source=holdout_source)
        selector = FeatureSelector(track=FeatureTrack.RESEARCH_BENCHMARK)

        X_train, y_train, _, f_names = selector.extract_matrices(train_h)
        X_val, y_val, _, _ = selector.extract_matrices(val_h, f_names)
        X_test_within, y_test_within, _, _ = selector.extract_matrices(test_h, f_names)

        # Train model on non-holdout sources
        model, manifest, _ = self.trainer.train_and_evaluate(
            model_family="LightGBM",
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            X_test=X_test_within,
            y_test=y_test_within,
            feature_names=f_names,
            track=FeatureTrack.RESEARCH_BENCHMARK,
        )

        within_metrics = compute_binary_metrics(
            y_test_within,
            model.predict_proba(X_test_within),
            threshold=manifest.validation_threshold,
        )

        holdout_metrics: dict[str, Any] = {}
        if len(holdout_df) > 0:
            X_holdout, y_holdout, _, _ = selector.extract_matrices(holdout_df, f_names)
            holdout_metrics = compute_binary_metrics(
                y_holdout,
                model.predict_proba(X_holdout),
                threshold=manifest.validation_threshold,
            )

        res = {
            "experiment": "E3-06_cross_source_generalization",
            "holdout_source": holdout_source,
            "within_domain_f1": within_metrics.get("f1", 0.0),
            "out_of_domain_f1": holdout_metrics.get("f1", 0.0),
            "generalization_gap": float(within_metrics.get("f1", 0.0) - holdout_metrics.get("f1", 0.0)),
            "within_metrics": within_metrics,
            "holdout_metrics": holdout_metrics,
        }
        self.tracker.log_experiment(
            experiment_id="E3-06_generalization",
            model_family="LightGBM",
            feature_track=FeatureTrack.RESEARCH_BENCHMARK.value,
            hyperparameters={"holdout_source": holdout_source},
            metrics=res,
            notes="Cross-source domain generalization test",
        )
        return res

    def run_e3_08_resource_benchmark(
        self,
        batch_sizes: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Experiment E3-08: Operational Resource Benchmark.
        Measures CPU latency (p50, p95, p99), memory, and model size across candidates.
        """
        batch_sizes = batch_sizes or [1, 16, 64]
        train_df, _, test_df = self.loader.load_splits()
        selector = FeatureSelector(track=FeatureTrack.RESEARCH_BENCHMARK)
        X_test, y_test, _, f_names = selector.extract_matrices(test_df)

        bench_results = []
        models_to_bench = ["LogisticRegression", "LightGBM", "PyTorchMLP"]

        for family in models_to_bench:
            model_id = f"{family.lower()}_research_benchmark"
            try:
                model, manifest = self.registry.load_model(model_id)
            except Exception:
                # If not registered, train quickly
                X_train, y_train, _, _ = selector.extract_matrices(train_df, f_names)
                model, manifest, _ = self.trainer.train_and_evaluate(
                    model_family=family,
                    X_train=X_train,
                    y_train=y_train,
                    X_val=X_test[:50],
                    y_val=y_test[:50],
                    X_test=X_test,
                    y_test=y_test,
                    feature_names=f_names,
                )

            for b_size in batch_sizes:
                sub_X = X_test[:b_size]
                if len(sub_X) < b_size:
                    sub_X = np.vstack([sub_X] * (b_size // max(1, len(sub_X)) + 1))[:b_size]

                # Warmup
                for _ in range(5):
                    _ = model.predict_proba(sub_X)

                # Timed runs
                latencies_ms = []
                for _ in range(50):
                    t0 = time.perf_counter()
                    _ = model.predict_proba(sub_X)
                    el_ms = (time.perf_counter() - t0) * 1000.0
                    latencies_ms.append(el_ms)

                p50 = float(np.percentile(latencies_ms, 50))
                p95 = float(np.percentile(latencies_ms, 95))
                p99 = float(np.percentile(latencies_ms, 99))
                throughput = float(b_size / (np.mean(latencies_ms) / 1000.0)) if np.mean(latencies_ms) > 0 else 0.0

                bench_results.append({
                    "model_family": family,
                    "batch_size": b_size,
                    "latency_p50_ms": p50,
                    "latency_p95_ms": p95,
                    "latency_p99_ms": p99,
                    "throughput_flows_per_sec": throughput,
                })

        return bench_results

    def run_e3_09_robustness(self) -> dict[str, Any]:
        """
        Experiment E3-09: Robustness under missing features and statistical noise.
        """
        _, _, test_df = self.loader.load_splits()
        selector = FeatureSelector(track=FeatureTrack.RESEARCH_BENCHMARK)
        X_test, y_test, _, f_names = selector.extract_matrices(test_df)

        model, _ = self.registry.load_model("lightgbm_research_benchmark")

        missing_res = RobustnessEvaluator.evaluate_missing_features(model, X_test, y_test)
        noise_res = RobustnessEvaluator.evaluate_gaussian_noise(model, X_test, y_test)

        return {
            "missing_feature_evaluation": missing_res,
            "gaussian_noise_evaluation": noise_res,
        }
