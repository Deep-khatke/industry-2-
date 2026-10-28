# Database Backup and Disaster Recovery Runbook

## 1. Objectives & SLAs
- **Recovery Point Objective (RPO):** $\le 5$ minutes of telemetry buffer.
- **Recovery Time Objective (RTO):** $\le 15$ minutes for ingestion and detection planes.
- **Strict Verification:** Every backup must include a SHA-256 cryptographic checksum.

## 2. Backup Procedure
Backups capture the transactional SQLite database, incident outbox state, action journal, and model manifests:
```bash
python -c "
from pathlib import Path
from fcs_pilot.governance.backup_recovery import BackupRecoveryManager
mgr = BackupRecoveryManager(Path('artifacts/phase9/backups'))
meta = mgr.create_state_backup('rural-isp-alpha', {'state': 'snapshot'})
print(f'Backup created: {meta.backup_id}, sha256={meta.sha256_checksum}')
"
```

## 3. Restoration & Integrity Verification
Before restoring into production, the snapshot is cryptographically verified:
1. Recompute SHA-256 checksum of raw backup file.
2. Verify checksum matches `sha256_checksum` in manifest.
3. Perform isolated sandbox extraction and row completeness verification.
4. Replace operational database file atomically using OS rename.
