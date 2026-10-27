# FCS Phase 3 — Operational Runbook & Reproduction Guide

**Architecture Baseline:** Federated Cyber Shield v1.2  
**Component:** FCS-ML Operational CLI (`fcs-ml`)  
**Budget:** Strictly ₹0 / $0  

---

## 1. Prerequisites and Environment Setup

Ensure Python 3.11+ is active in your virtual environment and all zero-cost dependencies are installed:

```bash
# Verify Python version
python --version  # Must be >= 3.11

# Verify all open-source packages
python -c "import polars, duckdb, sklearn, lightgbm, torch, pydantic; print('All ML dependencies present!')"
```

---

## 2. CLI Command Reference

All Phase 3 operations can be executed via the unified launcher:

```bash
# Via convenience script:
python tools/run_ml.py --help

# Or directly as a module:
python -m fcs_ml.cli --help
```

### Data Inspection & Verification

```bash
# Inspect available dataset splits, schemas, and row counts
python tools/run_ml.py inspect-data

# Cryptographically verify the Phase 2 dataset manifest and split artifacts
python tools/run_ml.py verify-data
```

### Candidate Model Training

```bash
# Train Logistic Regression on Deployable Feature Track (Track B)
python tools/run_ml.py train --model logistic --track deployable

# Train LightGBM on Research Feature Track (Track A)
python tools/run_ml.py train --model lightgbm --track research

# Train PyTorch MLP on Research Feature Track (Track A)
python tools/run_ml.py train --model mlp --track research --epochs 10

# Train 14-Class Multiclass Attack Classifier
python tools/run_ml.py train --task multiclass --track research
```

### Evaluation & Artifact Verification

```bash
# Evaluate a registered candidate model against the locked test split
python tools/run_ml.py evaluate --model-id lightgbm_deployable_subset

# Verify cryptographic SHA-256 integrity of a registered model artifact
python tools/run_ml.py verify-artifact --model-id lightgbm_deployable_subset

# Run operational CPU latency and throughput benchmark
python tools/run_ml.py benchmark

# Test operational single-record inference
python tools/run_ml.py predict --model-id lightgbm_deployable_subset
```

### Automated Benchmark Suite Execution

```bash
# Execute complete benchmark suite (E3-03, E3-04, E3-06, E3-08, E3-09)
python tools/run_ml.py run-all
```

---

## 3. Full Verification & Regression Testing

To run the complete automated test suite and regression checks:

```bash
# 1. Run Phase 3 ML tests (39 tests)
python -m pytest tests/ml-unit tests/ml-integration tests/ml-security tests/ml-reproducibility tests/ml-performance -v

# 2. Run full regression suite across Phase 1, Phase 2, and Phase 3 (132 tests)
python -m pytest tests/ -v

# 3. Check code style and linting
python -m ruff check .

# 4. Strict static type checking
python -m mypy -p fcs_ml -p fcs_udip -p packages -p adapters -p tools

# 5. Run automated Phase 3 verification suite (generates phase3_status.json)
python scripts/verify_phase3.py
```

---

## 4. Troubleshooting Guide

| Issue | Root Cause | Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'fcs_ml'` | `services/ml_training/src` missing from `PYTHONPATH` | Run via `python tools/run_ml.py` or export `PYTHONPATH="services/ml_training/src;services/dataset_pipeline/src;$PYTHONPATH"`. |
| `Artifact Verification FAILED` | File bytes on disk do not match manifest SHA-256 | Re-run training for that candidate model via `python tools/run_ml.py train --model <family>` or inspect for file tampering. |
| `TargetLeakageError: Prohibited column detected` | Attempted to include label, dataset, or split columns in predictors | Ensure feature selector uses predefined `FeatureTrack` rather than raw DataFrame columns. |
| `MLSecurityError: NaN or non-finite values` | Inference input vector contains invalid floating-point values | Filter or impute missing telemetry prior to scoring. The inference engine guarantees safe rejection. |
