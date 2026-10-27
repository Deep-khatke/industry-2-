# FCS Phase 3 — Candidate Model Selection & Justification

**Architecture Baseline:** Federated Cyber Shield v1.2  
**Component:** Model Selection Engine  
**Budget:** Strictly ₹0 / $0  

---

## 1. Selection Criteria Framework

Rather than declaring a single "universal winner" based solely on offline accuracy, Phase 3 evaluates candidate models across nine operational and scientific dimensions:

1. **Detection Quality:** PR-AUC and ROC-AUC on held-out test splits.
2. **False Alert Burden:** Operational False Positive Rate (FPR) at agreed recall floors.
3. **Cross-Source Transfer:** Robustness when evaluated on independent source holdouts.
4. **Probability Calibration:** Low Expected Calibration Error (ECE) for reliable threat scoring.
5. **Inference Latency:** Sub-millisecond CPU scoring for real-time edge telemetry.
6. **Throughput:** Bounded memory and high flow scoring rate on standard multi-core CPUs.
7. **Model Artifact Safety:** Non-executable format (no arbitrary Python pickles).
8. **Downstream Integration:** Compatibility with Phase 4 Manual Mode MVP and Phase 5 Hierarchical Multi-Model Detection (FCS-HMD).
9. **Federation Readiness:** Suitability for Flower-based federated averaging in Phase 6.

---

## 2. Selected Candidate Allocations

| Operational Role | Selected Model Candidate | Primary Justification | Runner-up / Non-selected Alternatives |
|---|---|---|---|
| **Primary Tabular Cloud Detector** (Phase 4 MVP) | **LightGBM (GBDT)** (`lightgbm_deployable_subset`) | **Highest PR-AUC (0.9530)**, highest throughput (**132,434 flows/s**), sub-millisecond p95 latency (0.456 ms), small footprint (24 KB), native text format. | *Logistic Regression* was rejected due to higher ECE (0.3524) and lower discriminative power (ROC-AUC 0.5757). |
| **Federated Learning Candidate** (Phase 6 FL) | **PyTorch Tabular MLP** (`pytorchmlp_research_benchmark`) | **Decoupled neural architecture (`TabularMLPNet`)**, deterministic parameter ordering, AdamW optimizer, lowest ECE (0.0493), safe `state_dict` export. Suitable for FedAvg. | *LightGBM* cannot be directly federated via standard FedAvg parameter averaging without complex ensemble tree serialization. |
| **Low-Footprint Edge Micro-Detector** | **Logistic Regression** (`logisticregression_deployable_subset`) | Interpretable linear weights, < 15 MB peak RAM, pure vector arithmetic ($1 / (1 + \exp(-z))$), zero external heavy library dependencies at runtime. | *DummyBaseline* was rejected as it provides zero genuine threat discrimination. |
| **Attack Category Specialist** (Phase 5 Diagnostic) | **Multiclass Attack Classifier** (`multiclassattackclassifier_research_benchmark`) | 14 canonical attack taxonomy mapping, explicit confidence calibration, built-in rejection/abstention mechanism for uncertain predictions. | Binary detectors cannot distinguish attack categories (e.g. DDoS vs Reconnaissance vs Botnet). |

---

## 3. Disqualification and Limitations of Other Models

1. **DummyBaseline Classifier:**
   - **Status:** Evaluated exclusively as a reference diagnostic baseline.
   - **Reason for Rejection:** Output reflects only dataset class priors (e.g., 88.04% attack). While achieving a misleadingly high F1 (0.9364), its ROC-AUC is exactly 0.5000 and its FPR is 1.0000. It is permanently disqualified from operational deployment.

2. **Uncalibrated Logistic Regression:**
   - **Status:** Retained solely as a lightweight edge baseline.
   - **Limitation:** Inability to capture complex multi-feature interactions in tabular NetFlow telemetry without explicit polynomial expansion.

3. **Complex Deep Learning Transformers (e.g. TabNet / FT-Transformer):**
   - **Status:** Not justified for tabular intrusion detection under ₹0 budget and CPU constraints.
   - **Reason for Rejection:** Massive training times, multi-hundred-megabyte memory footprints, and slow CPU latency without demonstrated performance gains over LightGBM on tabular network flows.
