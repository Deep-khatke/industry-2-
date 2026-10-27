# Federated Cyber Shield — Phase 2 Operational Runbook (FCS-UDIP)

**Architecture Baseline:** FCS v1.2  
**Component:** FCS-UDIP CLI Orchestrator & Workflow Manual  
**Command-Line Utility:** `python tools/fcs_data.py` (alias `fcs-data`)  

---

## 1. Quick Start: Automated End-to-End Run

To execute the entire 9-step FCS-UDIP pipeline in one command using the validated synthetic benchmark:

```bash
python tools/fcs_data.py run --input data/synthetic-fixtures/sample_netflow_v2.parquet --output-dir data/processed --seed 42
```

This automates:
1. Schema & Feature inspection (43 NetFlow v2 canonical columns)
2. Data quality checks & quarantine filtering
3. Attack label taxonomy normalization & subnet privacy masking
4. SHA-256 exact record deduplication
5. Leakage-safe group-aware train / validation / test splitting
6. Training-only preprocessor fitting (`preprocessor_state.json`)
7. Model-specific dataset export (General IDS, DDoS, Scanning, Botnet, Benign Anomaly)
8. Seven-client federated partitioning (IID, Moderate Non-IID, Strong Non-IID)
9. Signed manifest generation (`data/manifests/dataset_manifest_v1.json`) and audit reports

---

## 2. Step-by-Step CLI Execution

### Step 1: List and Inspect Dataset Sources
```bash
# List all registered sources and licensing status
python tools/fcs_data.py sources list

# Inspect detailed metadata for primary benchmark
python tools/fcs_data.py sources inspect NF-UQ-NIDS-v2
```

### Step 2: Verify Legal & Licensing Terms
```bash
# Verify intended academic research usage
python tools/fcs_data.py licenses verify NF-UQ-NIDS-v2 --use-case research

# Verify that commercial usage is strictly rejected
python tools/fcs_data.py licenses verify NF-UQ-NIDS-v2 --use-case commercial
```

### Step 3: Controlled Acquisition (Dry-Run & Real)
```bash
# Dry run: check disk budget and network constraints without downloading
python tools/fcs_data.py download --dry-run

# Download benchmark (requires network access and free disk space)
python tools/fcs_data.py download --dataset-id NF-UQ-NIDS-v2 --output-dir data/raw
```

### Step 4: Schema & Quality Inspection
```bash
# Inspect column schema and NetFlow feature family
python tools/fcs_data.py inspect data/synthetic-fixtures/sample_netflow_v2.parquet

# Clean corrupt records and segregate to quarantine
python tools/fcs_data.py validate data/synthetic-fixtures/sample_netflow_v2.parquet --output-clean data/processed/clean/clean.parquet --output-quarantine data/processed/quarantine/quarantine.parquet
```

### Step 5: Normalization & Privacy Masking
```bash
python tools/fcs_data.py normalize data/processed/clean/clean.parquet --source-id NF-UQ-NIDS-v2 --output data/processed/clean/normalized.parquet
```

### Step 6: Deduplication
```bash
python tools/fcs_data.py deduplicate data/processed/clean/normalized.parquet --mode exact --output data/processed/clean/dedup.parquet
```

### Step 7: Leakage-Safe Splitting
```bash
python tools/fcs_data.py split data/processed/clean/dedup.parquet --output-dir data/processed/splits --train-ratio 0.70 --val-ratio 0.15 --test-ratio 0.15 --seed 42
```

### Step 8: Training-Only Preprocessing
```bash
python tools/fcs_data.py preprocess data/processed/splits/train.parquet --val-file data/processed/splits/val.parquet --test-file data/processed/splits/test.parquet --output-dir data/processed/preprocessed
```

### Step 9: Model-Specific Exports
```bash
# General Binary IDS View
python tools/fcs_data.py export-general data/processed/preprocessed/train.parquet --output-dir data/processed/models/general

# Specialist Threat Views (DDoS, Scanning, Botnet, Anomaly)
python tools/fcs_data.py export-specialists data/processed/preprocessed/train.parquet --output-dir data/processed/models/specialists
```

### Step 10: Seven-Client Federated Partitioning
```bash
python tools/fcs_data.py partition data/processed/preprocessed/train.parquet --clients 7 --regime IID --output-dir data/processed/partitions/iid
python tools/fcs_data.py partition data/processed/preprocessed/train.parquet --clients 7 --regime STRONG_NON_IID --output-dir data/processed/partitions/strong_non_iid
```

### Step 11: Verify Manifest Cryptographic Signature
```bash
python tools/fcs_data.py verify-manifest --manifest data/manifests/dataset_manifest_v1.json
```

---

## 3. Troubleshooting & Failure Recovery

| Issue | Cause | Resolution |
| :--- | :--- | :--- |
| `TargetLeakageError` | Target column (`Attack`, `Label`, `dataset_source`, etc.) included in feature matrix $X$. | Check feature selection list; remove any target or provenance columns. |
| `LeakageDetectedError` | Group/subnet overlap between train and test partitions. | Verify that source subnets are disjoint or use group-aware splitting. |
| `ValueError: NetFlow v3 cannot be mixed with v2` | Attempting to combine 53-feature v3 data with 43-feature v2 data. | Reject v3 data or establish an explicit common projection. |
| `PermissionError: Commercial use prohibited` | Operation flagged with `COMMERCIAL` intent. | Reset usage flag to `RESEARCH_ONLY`. |
| Download budget exceeded | Dataset download exceeds the 1 GiB zero-cost bandwidth limit. | Use local fixtures or increase `--max-download-bytes` in `resource_limits.yaml`. |
