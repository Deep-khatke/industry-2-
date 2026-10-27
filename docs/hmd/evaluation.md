# FCS-HMD Empirical Evaluation & Benchmarks
## Comparative Experimental Analysis Across 6 Architectural Configurations & 7 Rural ISPs

**Subsystem:** FCS-HMD  
**Architecture:** Version 1.2  
**Dataset:** Locked Phase 2 Test Split (`test_split.parquet`): 209 flows (184 Attack, 25 Benign)  
**Execution Environment:** Local CPU Only (₹0.00 Incurred)  

---

## 1. Architectural Configuration Performance Comparison

| Configuration | Precision | Recall | F1-Score | PR-AUC | ROC-AUC | FPR | FNR | Brier | ECE |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **General Only** (`lightgbm_deployable_subset`) | 0.8804 | 1.0000 | 0.9364 | 0.9631 | 0.7528 | 1.0000 | 0.0000 | 0.1239 | 0.1103 |
| **General + Anomaly** (Level 1 Ensemble) | 0.8812 | 0.9674 | 0.9223 | 0.9623 | 0.7480 | 0.9600 | 0.0326 | 0.1534 | 0.2206 |
| **General + DDoS** (Volumetric Focus) | 0.8780 | 0.9783 | 0.9254 | 0.9587 | 0.7309 | 1.0000 | 0.0217 | 0.1557 | 0.2311 |
| **General + Scanning** (Recon Focus) | 0.8806 | 0.9620 | 0.9195 | 0.9535 | 0.6985 | 0.9600 | 0.0380 | 0.1312 | 0.1169 |
| **Hierarchical FCS-HMD** (Full Engine) | **0.8800** | **0.9565** | **0.9167** | **0.9509** | **0.6835** | **0.9600** | **0.0435** | **0.1330** | **0.1187** |
| **Learned Fusion Meta-Model** (Logistic) | 0.8804 | 1.0000 | 0.9364 | 0.9584 | 0.7246 | 1.0000 | 0.0000 | 0.1017 | 0.0804 |

---

## 2. Per-ISP Anomaly Baseline Evaluation (7 Simulated Rural ISPs)

| ISP Tenant | Evaluation Samples | Attack Infiltration | F1-Score | PR-AUC | FPR | Anomaly Isolation Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `rural-isp-alpha` | 147 | 131 | 0.5574 | 0.9598 | 0.0625 | ISOLATED & ACTIVE |
| `rural-isp-bravo` | 145 | 130 | 0.1678 | 0.9407 | 0.0667 | ISOLATED & ACTIVE |
| `rural-isp-charlie` | 143 | 128 | 0.5824 | 0.9647 | 0.0667 | ISOLATED & ACTIVE |
| `rural-isp-delta` | 142 | 127 | 0.3590 | 0.9613 | 0.0667 | ISOLATED & ACTIVE |
| `rural-isp-echo` | 141 | 126 | 0.7041 | 0.9753 | 0.0667 | ISOLATED & ACTIVE |
| `rural-isp-foxtrot` | 141 | 126 | 0.5730 | 0.9615 | 0.0667 | ISOLATED & ACTIVE |
| `rural-isp-golf` | 139 | 124 | 0.3333 | 0.9412 | 0.0667 | ISOLATED & ACTIVE |

---

## 3. System Latency & Resource Utilization

- **Conditional Model Router Overhead (p95):** $24.9\,\mu\text{s}$
- **Inference Latency (p50):** $6.696\,\text{ms}$
- **Inference Latency (p95):** $7.597\,\text{ms}$
- **Inference Latency (p99):** $8.276\,\text{ms}$
- **Resident Memory Usage:** $693.21\,\text{MB}$ ($+0.63\,\text{MB}$ delta during inference)
- **Zero-Cost Budget Compliance:** Strictly ₹0.00 incurred.
