# Federated Cyber Shield — Phase 3 ML Handoff Contract

**Architecture Baseline:** FCS v1.2  
**Handoff From:** Phase 2 — Unified Dataset Intelligence Pipeline (FCS-UDIP)  
**Handoff To:** Phase 3 — ML Model Development and Evaluation  
**Status:** READY FOR MODEL TRAINING  

---

## 1. Overview & Handoff Scope

Phase 2 has prepared versioned, leakage-safe, quality-validated, and cryptographically signed dataset artifacts ready for consumption by Phase 3 machine learning engineers. 

> [!IMPORTANT]
> **Zero Model Training in Phase 2:** In accordance with FCS architecture principles, Phase 2 did not train any final classifiers or anomaly models. All preprocessing parameters have been fitted strictly on training partitions and serialized for Phase 3 use.

---

## 2. Dataset Artifact Directory Map

Phase 3 ML pipelines should consume data exclusively from `data/processed/`:

```
data/processed/
├── preprocessed/
│   ├── train.parquet                   # Leakage-isolated preprocessed training set
│   ├── val.parquet                     # Leakage-isolated preprocessed validation set
│   ├── test.parquet                    # Untouched evaluation test set
│   ├── holdout_source_NF-ToN-IoT-v2.parquet # Out-of-domain independent testbed holdout
│   ├── split_manifest.json             # Group, time, and record assignment hashes
│   └── preprocessor_state.json         # Serialized medians, scalers, and bounds
│
├── models/
│   ├── general/
│   │   ├── train.parquet               # Binary classification (0 = Benign, 1 = Attack)
│   │   └── val.parquet                 # Binary validation set
│   │
│   └── specialists/
│       ├── ddos/
│       │   ├── train.parquet           # DDoS vs representative negatives
│       │   └── val.parquet
│       ├── scanning/
│       │   ├── train.parquet           # Reconnaissance/Scanning vs negatives
│       │   └── val.parquet
│       ├── botnet/
│       │   ├── train.parquet           # Botnet C2 telemetry vs negatives
│       │   └── val.parquet
│       └── benign_anomaly/
│           ├── train.parquet           # 100% clean benign baseline (unsupervised)
│           └── val.parquet             # Mixed benign and attack for evaluation
│
├── partitions/
│   ├── iid/                            # 7 simulated ISP client partitions (Balanced)
│   │   ├── isp_01.parquet ... isp_07.parquet
│   │   └── partition_manifest.json
│   ├── moderate_non_iid/               # Dirichlet alpha = 0.5
│   │   ├── isp_01.parquet ... isp_07.parquet
│   │   └── partition_manifest.json
│   └── strong_non_iid/                 # Dirichlet alpha = 0.1
│       ├── isp_01.parquet ... isp_07.parquet
│       └── partition_manifest.json
│
└── dataset_manifest.json               # Signed HMAC-SHA256 master dataset manifest
```

---

## 3. Python Ingestion Recipes for Phase 3 ML Engineers

### 3.1 Loading Research vs. Deployable Feature Matrices
```python
import polars as pl
from fcs_udip.harmonization.feature_harmonizer import FeatureHarmonizer

# 1. Load preprocessed training split
train_df = pl.read_parquet("data/processed/preprocessed/train.parquet")

harmonizer = FeatureHarmonizer()

# A. Extract Research Feature Matrix (43 canonical features)
X_research, y_binary, y_multi = harmonizer.get_research_feature_matrix(train_df, drop_raw_ips=True)

# B. Extract Deployable Feature Matrix (14 FlowEvent v1 features for live collector)
X_deployable, y_binary, y_multi = harmonizer.get_deployable_feature_matrix(train_df)

print(f"X_research shape:   {X_research.shape}")
print(f"X_deployable shape: {X_deployable.shape}")
```

### 3.2 Transforming Streaming Test Batches Using Frozen Preprocessor
```python
import polars as pl
from fcs_udip.preprocessing.preprocessor import TrainingOnlyPreprocessor

# Load frozen Phase 2 preprocessor state (DO NOT RE-FIT ON TEST DATA)
preprocessor = TrainingOnlyPreprocessor.load_state("data/processed/preprocessed/preprocessor_state.json")

# Transform new test or validation batches
test_df = pl.read_parquet("data/processed/preprocessed/test.parquet")
test_transformed = preprocessor.transform(test_df)
```

### 3.3 Loading Federated ISP Partitions for FL Simulation
```python
import polars as pl
from packages.contracts.partition_manifest import FederatedPartitionSetManifest

# Inspect partition manifest
manifest = FederatedPartitionSetManifest.from_file("data/processed/partitions/strong_non_iid/partition_manifest.json")
print(f"Regime: {manifest.partition_regime} | Total Records: {manifest.total_records}")

# Load client 1 local dataset (tenant-isp-alpha)
isp_01_df = pl.read_parquet("data/processed/partitions/strong_non_iid/isp_01.parquet")
print(f"ISP 01 records: {len(isp_01_df):,}")
```

---

## 4. Mandatory Phase 3 Constraints & Invariants

Phase 3 ML implementations MUST respect the following boundaries established in Phase 2:

1. **Anti-Leakage Guarantee:** Never include target columns (`Attack`, `Label`, `canonical_attack_label`, `binary_label`) or provenance columns (`dataset_source`, `isp_client_id`, `split_id`) as predictors in $X$.
2. **Preprocessing Invariance:** Never call `.fit()` or calculate normalization statistics on validation, test, or held-out source partitions.
3. **Federated Privacy Boundary:** Simulated client partitions `isp_01` to `isp_07` must be treated as physically separate siloed databases during federated training. Client data must never be pooled centrally prior to model training.
4. **Deployable Model Validation:** Models designated for production integration with the Phase 1 collector must be evaluated exclusively against `X_deployable`.
