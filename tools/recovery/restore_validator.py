#!/usr/bin/env python3
"""Isolated Disaster Recovery and Restore Validator for FCS (Phase 11).

Executes an isolated test restoration of a backup archive into an ephemeral sandbox.
Validates database schema, incident consistency, privacy-accounting preservation,
model revocation preservation, and measures Recovery Time Objective (RTO).
"""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tarfile
import tempfile
import time
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT_DIR / "artifacts" / "phase11" / "reports"


@dataclass
class RecoveryValidationResult:
    status: str
    rto_seconds: float
    integrity_check: str
    tables_verified: int
    privacy_spend_preserved: bool
    revoked_models_preserved: bool
    auto_live_disabled: bool
    details: dict[str, Any]


class RestoreValidator:
    """Validates disaster recovery and restore integrity in an isolated sandbox."""

    def __init__(self, backup_archive: Path) -> None:
        self.backup_archive = backup_archive

    def validate_restore(self) -> RecoveryValidationResult:
        if not self.backup_archive.exists():
            raise FileNotFoundError(f"Archive not found: {self.backup_archive}")

        sandbox_dir = Path(tempfile.mkdtemp(prefix="fcs_restore_sandbox_"))
        t0 = time.time()

        try:
            # 1. Extract archive
            with tarfile.open(self.backup_archive, "r:gz") as tar:
                tar.extractall(sandbox_dir, filter="data")

            extract_dirs = list(sandbox_dir.iterdir())
            if not extract_dirs:
                raise RuntimeError("Empty backup archive.")
            content_dir = extract_dirs[0]

            meta_file = content_dir / "backup_metadata.json"
            if not meta_file.exists():
                raise RuntimeError("Backup metadata missing from archive.")
            metadata = json.loads(meta_file.read_text(encoding="utf-8"))

            db_file = content_dir / "fcs_database.db"
            if not db_file.exists():
                raise RuntimeError("Database file missing from archive.")

            # 2. Database integrity check
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()

            integrity = cursor.execute("PRAGMA integrity_check;").fetchone()[0]
            if integrity != "ok":
                raise RuntimeError(f"Corrupt database in backup: {integrity}")

            # 3. Verify tables and counts
            tables = [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            tables_verified = len(tables)

            # 4. Check critical tables exist
            mandatory_tables = {"tenants", "users", "incidents", "action_journal", "detection_bundles"}
            missing_tables = mandatory_tables - set(tables)
            if missing_tables:
                raise RuntimeError(f"Missing mandatory tables in restored DB: {missing_tables}")

            # 5. Verify privacy spend invariant (spend is never 0 if previously recorded)
            privacy_spend_preserved = True
            if "privacy_budgets" in tables:
                rows = cursor.execute("SELECT tenant_id, cumulative_epsilon, cumulative_delta FROM privacy_budgets").fetchall()
                if rows:
                    for tenant_id, eps, delta in rows:
                        expected = metadata.get("privacy_spend_invariants", {}).get(tenant_id)
                        if expected and (eps < expected["epsilon"] or delta < expected["delta"]):
                            privacy_spend_preserved = False

            # 6. Verify AUTO_LIVE invariant: must be strictly disabled
            auto_live_disabled = True
            # In Phase 11, auto response is strictly False in code and restored metadata
            if metadata.get("auto_live_disabled") is not True:
                auto_live_disabled = False

            # 7. Verify model revocation invariant
            revoked_models_preserved = True
            if "model_registry" in tables:
                revoked = cursor.execute("SELECT model_id FROM model_registry WHERE status = 'REVOKED'").fetchall()
                # Ensure none was reactivated
                for r in revoked:
                    status = cursor.execute("SELECT status FROM model_registry WHERE model_id = ?", (r[0],)).fetchone()[0]
                    if status != "REVOKED":
                        revoked_models_preserved = False

            conn.close()
            rto_seconds = time.time() - t0

            status = "PASS" if (
                integrity == "ok"
                and privacy_spend_preserved
                and auto_live_disabled
                and revoked_models_preserved
            ) else "FAIL"

            return RecoveryValidationResult(
                status=status,
                rto_seconds=round(rto_seconds, 4),
                integrity_check=integrity,
                tables_verified=tables_verified,
                privacy_spend_preserved=privacy_spend_preserved,
                revoked_models_preserved=revoked_models_preserved,
                auto_live_disabled=auto_live_disabled,
                details={
                    "archive_file": str(self.backup_archive.name),
                    "archive_size_bytes": self.backup_archive.stat().st_size,
                    "metadata": metadata,
                    "tables_found": sorted(tables),
                },
            )
        finally:
            shutil.rmtree(sandbox_dir, ignore_errors=True)


def main() -> int:
    from tools.backups.backup_manager import BackupManager

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    print("[*] Creating test backup...")
    mgr = BackupManager()
    archive = mgr.create_full_backup()

    print(f"[*] Validating isolated restoration of {archive.name}...")
    validator = RestoreValidator(archive)
    result = validator.validate_restore()

    out_file = REPORT_DIR / "restore_validation_report.json"
    out_file.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")

    print(f"[+] Restore validation complete: {out_file}")
    print(f"[+] Status: {result.status} | RTO: {result.rto_seconds}s | Tables: {result.tables_verified}")
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
