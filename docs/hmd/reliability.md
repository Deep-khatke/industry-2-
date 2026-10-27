# FCS-HMD Reliability, Timeouts & Fallback Operations
## Fault Tolerance, Latency Budgets, and Recovery Procedures

**Subsystem:** FCS-HMD  
**Architecture:** Version 1.2  
**Implementation:** `services/ml_training/src/fcs_ml/hmd/executor.py`  

---

## 1. Reliability Architecture & Budgets

In high-throughput ISP network environments, an intrusion detection engine must not hang, leak memory, or crash when individual machine learning models experience timeouts or exceptions.

### Configured Latency Budgets
- **Per-Specialist Timeout Budget:** $100.0\,\text{ms}$ ($100,000\,\mu\text{s}$)
- **Total Pipeline Execution Ceiling:** $250.0\,\text{ms}$ ($250,000\,\mu\text{s}$)
- **Max Memory Footprint:** $1,024\,\text{MB}$ RSS

---

## 2. Failure Scenarios & Deterministic Fallback Matrix

| Failure Mode | Detection Mechanism | System Reaction | Emitted Status | Pipeline Impact |
|---|---|---|---|---|
| **Specialist Inference Timeout ($>100\,\text{ms}$)** | Wall-clock elapsed timer | Aborts specialist execution, returns timeout score | `ScoringStatus.TIMEOUT` | **Zero loss of coverage**: Level 1 general screening score preserved |
| **Specialist Model Exception / Crash** | Safe `try/except` wrapper around `predict_proba` | Traps exception, logs error traceback, records degraded status | `ScoringStatus.ERROR` | Preserves all remaining model scores |
| **Missing Model File in Registry** | `FileNotFoundError` during model load | Emits missing model placeholder with $0.0$ confidence | `ScoringStatus.MISSING` | Preserves general detection; never fabricates benign score |
| **Tampered Model Checksum** | SHA-256 verification in `BundleValidator` | Blocks bundle activation, preserves active bundle | `BundleValidationError` | Engine stays on active bundle; rejects deployment |
| **Corrupted DetectionBundle Manifest** | JSON schema or digest mismatch | Rejects bundle, logs audit alert | `BundleValidationError` | No change to operational state |
| **Tenant Anomaly Model Missing** | Registry tenant check | Falls back to global baseline | `FALLBACK_GLOBAL_BASELINE` | Screening continues with standard baseline |
| **Total Specialist Failure** | All routed specialists error/time out | Evidence fusion switches to `FALLBACK_GENERAL_ONLY` | Level 1 General Score | Threat detection continues |

---

## 3. Atomic Bundle Rollback Procedure

If a newly promoted detection bundle exhibits performance degradation or elevated false alerts:
1. Authorized Administrator invokes:
   `POST /v1/detection/bundle/rollback` (or `fcs-hmd bundles rollback`)
2. `HierarchicalDetectionEngine.rollback_bundle()` verifies `self._previous_bundle`.
3. Target bundle's SHA-256 digests are re-validated against the registry.
4. The previous bundle is restored atomically in memory and marked `ACTIVE`.
5. The degraded bundle is marked `ROLLED_BACK`.
6. All historical incident forensics and model score records remain permanently preserved in SQLite WAL storage.
