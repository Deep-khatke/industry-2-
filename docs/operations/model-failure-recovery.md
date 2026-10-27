# Federated Cyber Shield (FCS) v1.2 — Model Failure Recovery Guide
## Machine Learning Failure Modes, Safe Degradation & Fallback Procedures

**Status:** IMPLEMENTED & TESTED (Gate G06: PASS)  
**Active Model:** `lightgbm_deployable_subset` (14 NetFlow Features)  
**Fallback Strategy:** Deterministic Rules-Only Scoring (`RULES_ONLY`)  

---

## 1. Model Health States & Failure Hierarchy

To guarantee continuous operational resilience in the SOC, the FCS inference engine supports deterministic fallback handling:

```text
               Inference Request (30s Window)
                             │
                             ▼
                 [Artifact & Checksum Valid?]
                 ┌───────────┴───────────┐
                YES                      NO
                 │                       │
                 ▼                       ▼
      [Feature Contract Matches?]  Status: INVALID_ARTIFACT
      ┌──────────┴──────────┐            │
     YES                    NO           ▼
      │                      │     Fallback to RULES_ONLY
      ▼                      ▼
Status: READY        Status: FEATURE_MISMATCH
Evaluate Model               │
                             ▼
                       Fallback to RULES_ONLY
```

### Model Health Taxonomy

| State | Description | System Behavior | Incident Impact |
| :--- | :--- | :--- | :--- |
| `READY` | Candidate model loaded, SHA-256 verified, feature schema matches | Full hybrid ML + Rules detection | Full composite risk score (0–100) |
| `NOT_LOADED` | Model artifact directory missing or not initialized | Fallback to `RULES_ONLY` mode | Incidents generated via rules; ML marked `NOT_SCORED` |
| `INVALID_ARTIFACT` | Model file SHA-256 does not match signed manifest | Rejects execution; logs security alert | Fallback to `RULES_ONLY` mode |
| `FEATURE_MISMATCH` | Ingested window lacks required 14 NetFlow features | Rejects scoring; records schema divergence | Fallback to `RULES_ONLY` mode |
| `DEGRADED` | Inference latency exceeds 50ms CPU timeout budget | Bounded queue abort; fallback to rules | Rule matches preserved; latency logged |

> [!WARNING]
> **Safety Invariant:** Unscored traffic is never marked as benign. If ML inference fails or is unavailable, the system explicitly reports `status = "NOT_SCORED"` and relies solely on verified deterministic rules (FCS-R101 through FCS-R104).

---

## 2. Recovery Procedures

### 2.1 Resolving Artifact or Manifest Corruption
If `GET /v1/models/health` reports `INVALID_ARTIFACT`:
1. Inspect candidate model manifest:
   ```bash
   python -c "from fcs_ml.registry.registry import CandidateModelRegistry; r = CandidateModelRegistry(); print(r.verify_model_artifact('lightgbm_deployable_subset'))"
   ```
2. If corrupted, re-run Phase 3 model export:
   ```bash
   python services/ml_training/src/fcs_ml/benchmarks/evaluate.py
   ```
3. Restart the API service:
   ```bash
   fcs api start
   ```

### 2.2 Resolving Feature Contract Divergence
If `GET /v1/models/health` reports `FEATURE_MISMATCH`:
1. Verify that the window generator matches the locked 14-feature `deployable_v1` specification:
   - `in_bytes`, `in_pkts`, `flow_count`, `flow_duration_ms`
   - `protocol`, `tcp_flags`, `bytes_per_pkt`, `pkts_per_sec`, `bytes_per_sec`
   - `src_port_entropy`, `dst_port_entropy`, `unique_src_ips`, `unique_dst_ips`, `has_volume_anomaly`
2. Confirm that no synthetic zero-padding or unapproved feature modifications are present.
