# Phase 8 Backup and Restore Reliability Procedures

## 1. Scope & Objective
This runbook details reproducible backup and restore procedures for all persistent state in Federated Cyber Shield (FCS v1.2), including:
- Incident database (`fcs_phase4.db`)
- Action and audit journal tables
- Consortium ledger (`data/consortium_ledger.db`)
- Audit outbox (`data/governance_outbox.db`)
- Privacy budget accounting store (`artifacts/federation/privacy_budgets.sqlite`)
- Active model manifests and detection bundles

## 2. Development Hot Backup Procedure
FCS uses SQLite's atomic online backup API (`sqlite3.Connection.backup()`), allowing consistent snapshots without stopping active ingestion or locking read transactions:

```python
import sqlite3
from pathlib import Path

def create_online_backup(source_db_path: Path, backup_dest_path: Path) -> float:
    backup_dest_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(source_db_path)) as src, sqlite3.connect(str(backup_dest_path)) as dst:
        src.backup(dst, pages=100)
    return backup_dest_path.stat().st_size
```

## 3. Verified Development Restore Results
Tested under `tests/system/recovery/test_backup_restore.py` and Fault `F30`:

- **Backup Execution Duration:** `0.008 seconds` (< 2.0s SLA)
- **Restore Execution Duration:** `0.006 seconds` (< 2.0s SLA)
- **Tenant Table Completeness:** 7 of 7 tenants verified identical (100%)
- **User RBAC Table Completeness:** 100% records preserved
- **Incident History Completeness:** 100% records preserved
- **Duplicate Suppression:** Grouping keys and unique transaction IDs ensure zero duplicate incidents upon stream replay after restore.

## 4. Disaster Recovery Invariants
1. **Zero Secret Leakage:** No private keys (ECDSA / ML-DSA-65) or credentials are stored within database snapshots or committed to GitHub.
2. **Accountant Conservative Fallback:** If the privacy accountant database is restored from an older backup, it fails closed until reconciliation confirms no unrecorded privacy expenditure occurred.
3. **Model Activation Consistency:** Restoring an earlier database restores the verified active model pointer recorded in `detection_bundles`.

## 5. Production Requirements Pending (Phase 9)
- **Multi-Region Automated Snapshots:** AWS RDS / DynamoDB point-in-time recovery across multiple Availability Zones.
- **RTO / RPO Operational SLA:** Formal verification of Target RPO <= 5 minutes and RTO <= 15 minutes under simulated AWS datacenter failover.
