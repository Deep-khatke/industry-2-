#!/usr/bin/env python3
"""Atomic Backup Manager for FCS (Phase 11).

Performs consistent atomic SQLite WAL backups, archives model registry state,
preserves privacy-accounting spend state, action journals, and governance outbox.
"""

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tarfile
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_BACKUP_DIR = ROOT_DIR / "data" / "backups"


class BackupManager:
    """Manages consistent point-in-time backups of FCS platform state."""

    def __init__(self, db_path: Path | None = None, backup_dir: Path | None = None) -> None:
        self.db_path = db_path or (ROOT_DIR / "data" / "fcs_phase4.db")
        self.backup_dir = backup_dir or DEFAULT_BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_sqlite_online_backup(self, target_file: Path) -> dict[str, Any]:
        """Perform consistent online SQLite backup using sqlite3.backup API."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found at {self.db_path}")

        src = sqlite3.connect(str(self.db_path))
        dest = sqlite3.connect(str(target_file))
        with dest:
            src.backup(dest, pages=100)
        dest.close()
        src.close()

        hasher = hashlib.sha384()
        with open(target_file, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)

        return {
            "backup_file": str(target_file),
            "size_bytes": target_file.stat().st_size,
            "sha384": hasher.hexdigest(),
        }

    def create_full_backup(self) -> Path:
        """Create a complete consolidated backup archive containing DB, models, and metadata."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_staging = self.backup_dir / f"fcs_backup_staging_{timestamp}"
        backup_staging.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Atomic DB backup
            db_backup_path = backup_staging / "fcs_database.db"
            db_meta = self.create_sqlite_online_backup(db_backup_path)

            # 2. Extract snapshot of privacy spend & revocation invariants
            conn = sqlite3.connect(str(db_backup_path))
            cursor = conn.cursor()

            # Record table counts
            table_counts = {}
            for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
                tname = row[0]
                cnt = cursor.execute(f"SELECT COUNT(*) FROM {tname}").fetchone()[0]
                table_counts[tname] = cnt

            # Extract privacy spend
            privacy_spend = {}
            try:
                for row in cursor.execute("SELECT tenant_id, cumulative_epsilon, cumulative_delta FROM privacy_budgets").fetchall():
                    privacy_spend[row[0]] = {"epsilon": row[1], "delta": row[2]}
            except Exception:
                pass

            conn.close()

            # 3. Snapshot candidate model registry metadata
            models_dir = ROOT_DIR / "artifacts" / "candidate-models"
            models_snapshot = {}
            if models_dir.exists():
                for p in models_dir.glob("*.json"):
                    models_snapshot[p.name] = json.loads(p.read_text(encoding="utf-8"))

            metadata = {
                "backup_version": "1.2.0",
                "phase": "11-production-hardening",
                "created_at": datetime.now(UTC).isoformat(),
                "database_metadata": db_meta,
                "table_counts": table_counts,
                "privacy_spend_invariants": privacy_spend,
                "model_registry_snapshot": models_snapshot,
                "response_mode": "MANUAL",
                "auto_live_disabled": True,
            }

            meta_file = backup_staging / "backup_metadata.json"
            meta_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

            # 4. Create tar archive
            archive_path = self.backup_dir / f"fcs_backup_{timestamp}.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(backup_staging, arcname=f"fcs_backup_{timestamp}")

            return archive_path
        finally:
            if backup_staging.exists():
                shutil.rmtree(backup_staging)


def main() -> int:
    mgr = BackupManager()
    archive = mgr.create_full_backup()
    print(f"[+] Backup successfully generated: {archive}")
    print(f"[+] Archive size: {archive.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
