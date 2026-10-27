"""Backup and Restore Reliability Verification Suite for Phase 8."""

import sqlite3
import time
import pytest
from pathlib import Path
from fcs_api.database import init_db, seed_demo_data, get_db


@pytest.fixture
def populated_db(tmp_path):
    db_file = tmp_path / "origin.sqlite"
    seed_demo_data(db_path=str(db_file))
    return db_file


def test_sqlite_online_backup_and_restore(populated_db, tmp_path):
    """Verify online backup and subsequent restoration to an isolated location."""
    backup_file = tmp_path / "backup.sqlite"
    restored_file = tmp_path / "restored.sqlite"

    # 1. Execute online backup
    t0 = time.perf_counter()
    with sqlite3.connect(populated_db) as src, sqlite3.connect(backup_file) as dst:
        src.backup(dst, pages=100)
    backup_duration = time.perf_counter() - t0
    assert backup_file.exists()
    assert backup_duration < 2.0, "Backup must complete within development SLA"

    # 2. Restore to isolated target
    t1 = time.perf_counter()
    with sqlite3.connect(backup_file) as bkp, sqlite3.connect(restored_file) as res:
        bkp.backup(res, pages=100)
    restore_duration = time.perf_counter() - t1
    assert restored_file.exists()
    assert restore_duration < 2.0, "Restore must complete within development SLA"

    # 3. Data completeness check
    with sqlite3.connect(populated_db) as orig, sqlite3.connect(restored_file) as rest:
        orig_tenants = orig.execute("SELECT COUNT(*) FROM tenants").fetchone()[0]
        rest_tenants = rest.execute("SELECT COUNT(*) FROM tenants").fetchone()[0]
        assert orig_tenants == rest_tenants == 7, "Tenant count mismatch after restore"

        orig_users = orig.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        rest_users = rest.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        assert orig_users == rest_users, "User count mismatch after restore"

        orig_incidents = orig.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
        rest_incidents = rest.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
        assert orig_incidents == rest_incidents, "Incident count mismatch after restore"
