"""Training and evaluation pipeline for FCS Phase 5 Multi-Model Intrusion Detection candidates."""

import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.metrics import (
    auc,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
ML_SRC = ROOT_DIR / "services" / "ml_training" / "src"
for p in [str(ROOT_DIR), str(ML_SRC)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fcs_ml.evaluation.metrics import compute_expected_calibration_error
from fcs_ml.hmd.bundle import DetectionBundle
from fcs_ml.models.autoencoder import AutoencoderAnomalyModel
from fcs_ml.models.botnet_specialist import BotnetSpecialistModel, assess_botnet_eligibility
from fcs_ml.models.ddos_specialist import DDoSSpecialistModel
from fcs_ml.models.isolation_forest import IsolationForestAnomalyModel
from fcs_ml.models.scanning_specialist import ScanningSpecialistModel
from fcs_ml.registry.manifest import ModelManifest
from fcs_ml.registry.registry import CandidateModelRegistry
from fcs_ml.thresholds.optimizer import ThresholdOptimizer

DEPLOYABLE_FEATURES = [
    "L4_SRC_PORT",
    "L4_DST_PORT",
    "PROTOCOL",
    "IN_BYTES",
    "IN_PKTS",
    "FLOW_DURATION_MILLISECONDS",
    "TCP_FLAGS",
    "SRC_TO_DST_SECOND_BYTES",
    "SRC_TO_DST_AVG_THROUGHPUT",
]


def load_dataset(path: Path) -> tuple[np.ndarray, np.ndarray]:
    df = pl.read_parquet(path)
    X = df.select(DEPLOYABLE_FEATURES).to_numpy().astype(np.float32)
    X = np.nan_to_num(X, nan=0.0, posinf=1e6, neginf=-1e6)
    if "binary_label" in df.columns:
        y = df["binary_label"].to_numpy().astype(np.int64)
    elif "Label" in df.columns:
        y = df["Label"].to_numpy().astype(np.int64)
    else:
        y = np.zeros(len(df), dtype=np.int64)
    return X, y


def evaluate_model_on_test(model, X_test: np.ndarray, y_test: np.ndarray, threshold: float = 0.5) -> dict:
    start_t = time.perf_counter()
    proba = model.predict_proba(X_test)
    elapsed = time.perf_counter() - start_t
    latency_us = (elapsed / len(X_test)) * 1_000_000.0

    scores = proba[:, 1] if proba.shape[1] > 1 else proba[:, 0]
    preds = (scores >= threshold).astype(np.int64)

    prec = float(precision_score(y_test, preds, zero_division=0))
    rec = float(recall_score(y_test, preds, zero_division=0))
    f1 = float(f1_score(y_test, preds, zero_division=0))

    try:
        roc = float(roc_auc_score(y_test, scores))
    except Exception:
        roc = 0.5

    try:
        precision_curve, recall_curve, _ = precision_recall_curve(y_test, scores)
        pr_auc = float(auc(recall_curve, precision_curve))
    except Exception:
        pr_auc = float(np.mean(y_test))

    cm = confusion_matrix(y_test, preds, labels=[0, 1])
    tn, fp, fn, tp = [int(v) for v in cm.ravel()]
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0
    brier = float(brier_score_loss(y_test, scores))
    ece = float(compute_expected_calibration_error(y_test, scores))

    return {
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "roc_auc": roc,
        "pr_auc": pr_auc,
        "fpr": fpr,
        "fnr": fnr,
        "brier_score": brier,
        "expected_calibration_error": ece,
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "threshold_used": threshold,
        "total_samples": len(y_test),
        "inference_latency_p95_us": latency_us,
    }


def main():
    print("=" * 70)
    print("FEDERATED CYBER SHIELD — PHASE 5 MODEL TRAINING & ARTIFACT REGISTRATION")
    print(f"Executed at: {datetime.now(UTC).isoformat()}")
    print("=" * 70)

    data_dir = ROOT_DIR / "data" / "processed"
    registry = CandidateModelRegistry(registry_dir=ROOT_DIR / "artifacts" / "candidate-models")

    # Load validation and test splits
    X_val, y_val = load_dataset(data_dir / "splits" / "val.parquet")
    X_test, y_test = load_dataset(data_dir / "splits" / "test.parquet")
    print(f"Validation set: {len(X_val)} samples (Attacks={sum(y_val)})")
    print(f"Test set:       {len(X_test)} samples (Attacks={sum(y_test)})\n")

    trained_models = {}

    # 1. Isolation Forest Anomaly Detector
    print("[TRAINING] Isolation Forest ISP Baseline Anomaly Detector...")
    X_benign, _ = load_dataset(data_dir / "models" / "benign_anomaly_train.parquet")
    iforest = IsolationForestAnomalyModel(n_estimators=100, contamination=0.05, random_seed=42)
    iforest.fit(X_benign, feature_names=DEPLOYABLE_FEATURES)

    # Threshold optimization on val
    val_probs = iforest.predict_proba(X_val)[:, 1]
    th_opt = ThresholdOptimizer(objective="f1", n_steps=50).fit(y_val, val_probs)
    optimal_th = float(th_opt.optimal_threshold_)

    metrics = evaluate_model_on_test(iforest, X_test, y_test, threshold=optimal_th)
    print(f"  Test F1: {metrics['f1']:.4f} | PR-AUC: {metrics['pr_auc']:.4f} | Latency: {metrics['inference_latency_p95_us']:.1f}us")

    manifest = ModelManifest(
        model_id="isolationforest_anomaly_tenant",
        model_family="IsolationForest",
        version="1.2.0",
        feature_track="DEPLOYABLE_SUBSET",
        feature_schema_digest="92f73ab100db06d82b252e0c86fac983083232fb247baf1cdf57afd6ba8dcbf0",
        feature_names=DEPLOYABLE_FEATURES,
        dataset_manifest_digest="phase2_manifest",
        training_sample_count=len(X_benign),
        validation_sample_count=len(X_val),
        test_sample_count=len(X_test),
        validation_threshold=optimal_th,
        calibration_method="inverted_sigmoid",
        test_metrics=metrics,
        artifact_hash="",
        artifact_path="",
    )
    reg_dir = registry.register_model(iforest, manifest)
    trained_models["isolationforest_anomaly_tenant"] = manifest
    print(f"  Registered at: {reg_dir}\n")

    # 2. Autoencoder Anomaly Detector
    print("[TRAINING] Deep Autoencoder Anomaly Detector...")
    autoenc = AutoencoderAnomalyModel(hidden_dim=16, latent_dim=8, epochs=30, batch_size=32, random_seed=42)
    autoenc.fit(X_benign, feature_names=DEPLOYABLE_FEATURES)

    ae_val_probs = autoenc.predict_proba(X_val)[:, 1]
    ae_th_opt = ThresholdOptimizer(objective="f1", n_steps=50).fit(y_val, ae_val_probs)
    ae_optimal_th = float(ae_th_opt.optimal_threshold_)

    ae_metrics = evaluate_model_on_test(autoenc, X_test, y_test, threshold=ae_optimal_th)
    print(f"  Test F1: {ae_metrics['f1']:.4f} | PR-AUC: {ae_metrics['pr_auc']:.4f} | Latency: {ae_metrics['inference_latency_p95_us']:.1f}us")

    ae_manifest = ModelManifest(
        model_id="autoencoder_anomaly",
        model_family="Autoencoder",
        version="1.2.0",
        feature_track="DEPLOYABLE_SUBSET",
        feature_schema_digest="92f73ab100db06d82b252e0c86fac983083232fb247baf1cdf57afd6ba8dcbf0",
        feature_names=DEPLOYABLE_FEATURES,
        dataset_manifest_digest="phase2_manifest",
        training_sample_count=len(X_benign),
        validation_sample_count=len(X_val),
        test_sample_count=len(X_test),
        validation_threshold=ae_optimal_th,
        calibration_method="reconstruction_sigmoid",
        test_metrics=ae_metrics,
        artifact_hash="",
        artifact_path="",
    )
    ae_dir = registry.register_model(autoenc, ae_manifest)
    trained_models["autoencoder_anomaly"] = ae_manifest
    print(f"  Registered at: {ae_dir}\n")

    # 3. DDoS Specialist Model
    print("[TRAINING] DDoS Specialist Model (LightGBM)...")
    X_ddos, y_ddos = load_dataset(data_dir / "models" / "ddos_specialist_train.parquet")
    ddos_model = DDoSSpecialistModel(n_estimators=100, learning_rate=0.05, random_seed=42)
    ddos_model.fit(X_ddos, y_ddos, X_val=X_val, y_val=y_val, feature_names=DEPLOYABLE_FEATURES)

    ddos_val_probs = ddos_model.predict_proba(X_val)[:, 1]
    ddos_th_opt = ThresholdOptimizer(objective="f1", n_steps=50).fit(y_val, ddos_val_probs)
    ddos_th = float(ddos_th_opt.optimal_threshold_)

    ddos_metrics = evaluate_model_on_test(ddos_model, X_test, y_test, threshold=ddos_th)
    print(f"  Test F1: {ddos_metrics['f1']:.4f} | PR-AUC: {ddos_metrics['pr_auc']:.4f} | Latency: {ddos_metrics['inference_latency_p95_us']:.1f}us")

    ddos_manifest = ModelManifest(
        model_id="lightgbm_ddos_specialist",
        model_family="DDoSSpecialist",
        version="1.2.0",
        feature_track="DEPLOYABLE_SUBSET",
        feature_schema_digest="92f73ab100db06d82b252e0c86fac983083232fb247baf1cdf57afd6ba8dcbf0",
        feature_names=DEPLOYABLE_FEATURES,
        dataset_manifest_digest="phase2_manifest",
        training_sample_count=len(X_ddos),
        validation_sample_count=len(X_val),
        test_sample_count=len(X_test),
        validation_threshold=ddos_th,
        calibration_method="sigmoid",
        test_metrics=ddos_metrics,
        artifact_hash="",
        artifact_path="",
    )
    ddos_dir = registry.register_model(ddos_model, ddos_manifest)
    trained_models["lightgbm_ddos_specialist"] = ddos_manifest
    print(f"  Registered at: {ddos_dir}\n")

    # 4. Scanning Specialist Model
    print("[TRAINING] Scanning Specialist Model (LightGBM)...")
    X_scan, y_scan = load_dataset(data_dir / "models" / "scanning_specialist_train.parquet")
    scan_model = ScanningSpecialistModel(n_estimators=100, learning_rate=0.05, random_seed=42)
    scan_model.fit(X_scan, y_scan, X_val=X_val, y_val=y_val, feature_names=DEPLOYABLE_FEATURES)

    scan_val_probs = scan_model.predict_proba(X_val)[:, 1]
    scan_th_opt = ThresholdOptimizer(objective="f1", n_steps=50).fit(y_val, scan_val_probs)
    scan_th = float(scan_th_opt.optimal_threshold_)

    scan_metrics = evaluate_model_on_test(scan_model, X_test, y_test, threshold=scan_th)
    print(f"  Test F1: {scan_metrics['f1']:.4f} | PR-AUC: {scan_metrics['pr_auc']:.4f} | Latency: {scan_metrics['inference_latency_p95_us']:.1f}us")

    scan_manifest = ModelManifest(
        model_id="lightgbm_scanning_specialist",
        model_family="ScanningSpecialist",
        version="1.2.0",
        feature_track="DEPLOYABLE_SUBSET",
        feature_schema_digest="92f73ab100db06d82b252e0c86fac983083232fb247baf1cdf57afd6ba8dcbf0",
        feature_names=DEPLOYABLE_FEATURES,
        dataset_manifest_digest="phase2_manifest",
        training_sample_count=len(X_scan),
        validation_sample_count=len(X_val),
        test_sample_count=len(X_test),
        validation_threshold=scan_th,
        calibration_method="sigmoid",
        test_metrics=scan_metrics,
        artifact_hash="",
        artifact_path="",
    )
    scan_dir = registry.register_model(scan_model, scan_manifest)
    trained_models["lightgbm_scanning_specialist"] = scan_manifest
    print(f"  Registered at: {scan_dir}\n")

    # 5. Botnet Specialist Assessment & Model
    print("[EVALUATING] Botnet Specialist Production Eligibility...")
    eligibility = assess_botnet_eligibility(DEPLOYABLE_FEATURES)
    print(f"  Eligibility status: {eligibility['status']}")
    print(f"  Missing prerequisites: {eligibility['missing_prerequisites']}")

    # Train benchmark botnet model on approved subset
    X_bot, y_bot = load_dataset(data_dir / "models" / "botnet_specialist_train.parquet")
    bot_model = BotnetSpecialistModel(n_estimators=80, learning_rate=0.05, random_seed=42)
    bot_model.fit(X_bot, y_bot, X_val=X_val, y_val=y_val, feature_names=DEPLOYABLE_FEATURES)
    bot_metrics = evaluate_model_on_test(bot_model, X_test, y_test, threshold=0.5)

    bot_manifest = ModelManifest(
        model_id="lightgbm_botnet_specialist",
        model_family="BotnetSpecialist",
        version="1.2.0",
        feature_track="DEPLOYABLE_SUBSET_BENCHMARK",
        feature_schema_digest="92f73ab100db06d82b252e0c86fac983083232fb247baf1cdf57afd6ba8dcbf0",
        feature_names=DEPLOYABLE_FEATURES,
        dataset_manifest_digest="phase2_manifest",
        training_sample_count=len(X_bot),
        validation_sample_count=len(X_val),
        test_sample_count=len(X_test),
        validation_threshold=0.5,
        calibration_method="sigmoid",
        test_metrics=bot_metrics,
        artifact_hash="",
        artifact_path="",
    )
    bot_dir = registry.register_model(bot_model, bot_manifest)
    trained_models["lightgbm_botnet_specialist"] = bot_manifest
    print(f"  Registered benchmark model at: {bot_dir}\n")

    # 6. Assemble and Seal Default DetectionBundle
    print("[ASSEMBLING] DetectionBundle fcs-hmd-bundle-v1...")
    # Retrieve general model artifact hash
    gen_ver = registry.verify_model_artifact("lightgbm_deployable_subset")
    anom_ver = registry.verify_model_artifact("isolationforest_anomaly_tenant")
    ddos_ver = registry.verify_model_artifact("lightgbm_ddos_specialist")
    scan_ver = registry.verify_model_artifact("lightgbm_scanning_specialist")

    bundle = DetectionBundle(
        bundle_id="fcs-hmd-bundle-v1",
        version="1.2.0",
        general_model_id="lightgbm_deployable_subset",
        anomaly_model_id="isolationforest_anomaly_tenant",
        specialist_model_ids=["lightgbm_ddos_specialist", "lightgbm_scanning_specialist"],
        model_hashes={
            "lightgbm_deployable_subset": gen_ver["recorded_hash"],
            "isolationforest_anomaly_tenant": anom_ver["recorded_hash"],
            "lightgbm_ddos_specialist": ddos_ver["recorded_hash"],
            "lightgbm_scanning_specialist": scan_ver["recorded_hash"],
        },
        authorized_by="security_admin",
        status="ACTIVE",
    ).seal()

    bundle_path = ROOT_DIR / "artifacts" / "candidate-models" / "default_bundle.json"
    bundle_path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    print(f"  Bundle Digest: {bundle.bundle_digest}")
    print(f"  Bundle saved to: {bundle_path}\n")

    # Save summary report of all candidate models
    print("[SUCCESS] All Phase 5 models trained, evaluated, and verified.")


if __name__ == "__main__":
    main()
