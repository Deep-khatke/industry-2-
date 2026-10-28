# Compliance & Data Retention Schedule

## 1. Schedule & Purpose
| Telemetry Category | Max Retention | Legal / Operational Justification | Action on Expiry |
|---|---|---|---|
| Raw NetFlow / IPFIX Packets | 7 Days | Short-term traffic analysis and initial triage | Secure age-based deletion |
| Aggregated Feature Windows | 14 Days | Model inference and rolling drift detection | Automated purge |
| Incident Evidence Bundles | 90 Days | SOC incident investigation & audit review | Cryptographic archive then purge |
| Analyst Feedback Records | 180 Days | Human ground truth verification for retraining | Retain until dataset manifest sealed |
| Action Journal Audit Logs | 365 Days | Proof of defensive response compliance | Immutable legal hold |
| Privacy Accounting Receipts | 730 Days | Proof of differential privacy epsilon budget | Permanent ledger storage |

## 2. Automated Rolling Purge
The `DataRetentionManager` evaluates items against the retention schedule daily. Active incidents under investigation are protected from premature pruning.
