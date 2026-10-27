# FCS-UDIP Data Quality Audit Report
**Dataset ID:** `NF-UQ-NIDS-v2`
**Audit Timestamp:** 2026-10-25T14:20:53.361972+00:00
**Pipeline Standard:** FCS v1.2 Phase 2 Data Quality Framework

---

## 1. Quality Summary Metrics
| Metric | Value | Proportion |
|---|---|---|
| **Initial Ingested Rows** | 1,400 | 100.00% |
| **Accepted Clean Rows** | 1,400 | 100.00% |
| **Quarantined Rows** | 0 | 0.00% |
| **Immutability of Raw Source** | **PRESERVED** | 100.00% |

---

## 2. Rule Violation Breakdown
| Quality Rule Triggered | Affected Row Count | Percentage |
|---|---|---|
| *None* | 0 | 0.00% |


---

## 3. Quarantine Remediation Policy
- Records triggering out-of-bounds port numbers, negative packet counts, negative byte counts, or missing labels are segregated into `data/staging/quarantine/`.
- Quarantined records are preserved for forensic review and model robustness ablation.
- Under FCS v1.2 policy, zero rows are silently deleted without audit tracking.
