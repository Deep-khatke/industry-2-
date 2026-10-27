# FCS Phase 3 — Machine Learning Training Architecture

**Architecture Baseline:** Federated Cyber Shield v1.2  
**Component:** FCS-ML Training & Candidate Registry System  
**Budget:** Strictly ₹0 / $0 (CPU compatible, local artifacts)  

---

## 1. Executive Overview

Phase 3 introduces the machine learning model development, training, and benchmarking foundation for Federated Cyber Shield (FCS). Continuing directly from Phase 1 (Ingestion & Multi-Tenancy) and Phase 2 (Unified Dataset Intelligence Pipeline, FCS-UDIP), Phase 3 converts validated cybersecurity telemetry and tabular dataset splits into candidate threat-detection models.

The system enforces modularity, data-leakage immunity, zero-cost CPU execution, and verifiable artifact integrity.

```
+-----------------------------------------------------------------------------------+
|                           PHASE 3 ML TRAINING PIPELINE                            |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  +--------------------------------+       +------------------------------------+  |
|  | Locked Dataset Splits (Ph. 2)  | ----> | DatasetLoader & Manifest Verifier  |  |
|  | - train.parquet                |       | - Verifies HMAC-SHA256 signature   |  |
|  | - val.parquet                  |       | - Enforces memory & row bounds     |  |
|  | - test.parquet                 |       +------------------------------------+  |
|  +--------------------------------+                          |                    |
|                                                              v                    |
|  +--------------------------------+       +------------------------------------+  |
|  | Feature & Anti-Leakage Guard   | <---- | FeatureSelector                    |  |
|  | - Rejects Attack, Source IDs   |       | - Track A: Research (43 features)  |  |
|  | - Verifies schema digests      |       | - Track B: Deployable (14 feats)   |  |
|  +--------------------------------+       +------------------------------------+  |
|                                                              |                    |
|                                                              v                    |
|  +-----------------------------------------------------------------------------+  |
|  | Model Training Matrix (Strictly training split for fitting & scaling)        |  |
|  |  +-------------------+  +-------------------+  +--------------------------+ |  |
|  |  | DummyBaseline     |  | LogisticRegression|  | LightGBM GBDT            | |  |
|  |  | Non-predictive    |  | Training scaler   |  | Early stopping on val    | |  |
|  |  +-------------------+  +-------------------+  +--------------------------+ |  |
|  |  +------------------------------------------+  +--------------------------+ |  |
|  |  | PyTorch Tabular MLP                      |  | Multiclass Classifier    | |  |
|  |  | CPU mini-batch, AdamW, Flower-ready      |  | 14 categories + abstain  | |  |
|  |  +------------------------------------------+  +--------------------------+ |  |
|  +-----------------------------------------------------------------------------+  |
|                                                              |                    |
|                                                              v                    |
|  +--------------------------------+       +------------------------------------+  |
|  | ThresholdOptimizer (Val only)  | ----> | ProbabilityCalibrator (Val only)   |  |
|  | - F1 max / FPR budget floors   |       | - Platt Sigmoid / Isotonic         |  |
|  +--------------------------------+       +------------------------------------+  |
|                                                              |                    |
|                                                              v                    |
|  +--------------------------------+       +------------------------------------+  |
|  | Final Evaluation (Test Split)  | ----> | CandidateModelRegistry             |  |
|  | - Zero threshold retraining    |       | - Non-executable safe formats      |  |
|  | - Cross-source domain shift    |       | - ModelManifest v1 with SHA-256    |  |
|  +--------------------------------+       +------------------------------------+  |
|                                                              |                    |
|                                                              v                    |
|  +-----------------------------------------------------------------------------+  |
|  | Safe InferenceEngine (Phase 4 MVP, Phase 5 HMD, Phase 6 Flower Handoff)      |  |
|  | - Single & batch flow scoring; GUARANTEED 0 NETWORK/FIREWALL SIDE EFFECTS   |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Core Modules and Interfaces

The training system resides in `services/ml_training/src/fcs_ml/`:

| Module Path | Primary Class / Function | Responsibility |
|---|---|---|
| `data/loader.py` | `DatasetLoader` | Stream-safe Parquet loader with cryptographic manifest verification and row limits. |
| `data/dataset.py` | `TabularDataset`, `create_dataloader` | PyTorch Dataset and DataLoader abstractions with deterministic seeding. |
| `features/selector.py` | `FeatureSelector`, `FeatureTrack` | Strict feature extraction for Track A and Track B; target/source leakage prevention. |
| `models/base.py` | `BaseFCSModel` | Common abstract interface for candidate models (`fit`, `predict`, `predict_proba`, `save`, `load`). |
| `models/baseline.py` | `DummyBaselineClassifier` | Non-predictive prior-frequency baseline for calibrating class-imbalance effects. |
| `models/logistic.py` | `LogisticRegressionModel` | Scikit-learn Logistic Regression with training-only `StandardScaler` and native JSON weight export. |
| `models/lightgbm_model.py` | `LightGBMModel` | Gradient boosted trees with bounded CPU threads, early stopping, and native text model representation. |
| `models/mlp.py` | `PyTorchMLPModel`, `TabularMLPNet` | Deep tabular neural network with AdamW, batch training, early stopping, and `state_dict` export. |
| `models/multiclass.py` | `MulticlassAttackClassifier` | 14-class attack classifier with explicit prediction uncertainty and rejection mechanisms. |
| `thresholds/optimizer.py` | `ThresholdOptimizer` | Validation-only threshold optimization (Max F1, target FPR floor). |
| `calibration/calibrator.py` | `ProbabilityCalibrator` | Probability calibration (Platt sigmoid and isotonic regression) fitted strictly on validation data. |
| `evaluation/metrics.py` | `compute_binary_metrics`, `compute_multiclass_metrics`, `compute_expected_calibration_error` | Standardized evaluation reporting across PR-AUC, ROC-AUC, F1, FPR, and ECE. |
| `evaluation/robustness.py` | `RobustnessEvaluator` | Perturbation analysis testing missing feature inputs and zero-mean Gaussian feature noise. |
| `registry/manifest.py` | `ModelManifest` | Cryptographic model metadata specification matching Architecture v1.2. |
| `registry/registry.py` | `CandidateModelRegistry` | Local disk registry with SHA-256 artifact checksum verification. |
| `inference/engine.py` | `InferenceEngine` | Operational scoring interface with guaranteed zero network side effects. |
| `export/exporter.py` | `ModelExporter` | Bundles candidate model, preprocessing specs, thresholds, and manifests into deployment bundles. |
| `security/validator.py` | `MLSecurityValidator` | Enforces runtime input invariants, schema conformity, and dimension boundaries. |

---

## 3. Two Feature Experiment Tracks

In accordance with Phase 3 specifications, the training pipeline maintains two completely independent feature experiment tracks:

1. **Track A — Research Benchmark (`RESEARCH_BENCHMARK`):**
   - **Features:** 43 standardized network features from the unified NF-UQ-NIDS-v2 dataset.
   - **Purpose:** Academic benchmarking against public intrusion-detection literature.
   - **Caveat:** High feature count includes specialized flow statistics that may not be available on standard ISP edge routers without deep state inspection.

2. **Track B — Deployable Feature Subset (`DEPLOYABLE_SUBSET`):**
   - **Features:** 14 core NetFlow/IPFIX fields directly compatible with the Phase 1 `FlowEvent` v1 contract (`L4_SRC_PORT`, `L4_DST_PORT`, `PROTOCOL`, `L7_PROTO`, `IN_BYTES`, `OUT_BYTES`, `IN_PKTS`, `OUT_PKTS`, `TCP_FLAGS`, `FLOW_DURATION_MILLISECONDS`, etc.).
   - **Purpose:** Realistic edge deployment feasibility.
   - **Status:** Evaluated side-by-side with Track A to quantify the exact detection degradation when operating under constrained telemetry.

---

## 4. Leakage Prevention Protocol

Data leakage renders offline cybersecurity benchmarks invalid. FCS Phase 3 strictly enforces:
- **Preprocessing Isolation:** Numeric scalers (`StandardScaler`) and calibrators are fit *only* on the training split. Validation and test splits are strictly transformed using frozen parameters.
- **Prohibited Predictor Filtering:** `FeatureSelector` automatically strips all label columns (`Attack`, `Label`, `binary_label`), source identifiers (`Dataset`, `source_dataset`), split identifiers (`split_name`, `fold`), and ISP partition metadata. Attempting to select a prohibited column raises `TargetLeakageError`.
- **Threshold Freezing:** Thresholds are selected using the validation split *only*. The test split is evaluated once under the frozen threshold.
- **Split Preservation:** Train, validation, and test splits generated and signed by Phase 2 in `data/processed/splits/` are treated as immutable read-only artifacts.
