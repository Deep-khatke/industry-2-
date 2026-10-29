"""Phase 11: Fault Injection, Graceful Degradation, and Recovery Tests."""

from pathlib import Path
import pytest

from fcs_api.detection.service import DetectionService
from tools.backups.backup_manager import BackupManager
from tools.recovery.restore_validator import RestoreValidator


def test_corrupt_model_artifact_graceful_degradation():
    """Verify DetectionService safely falls back to RULES_ONLY if model registry is missing/corrupted."""
    service = DetectionService(model_registry_dir="non_existent_corrupted_directory")
    health = service.get_model_health()

    assert health["fallback_mode"] == "RULES_ONLY"
    assert health["security_invariant"] == "network_action_executed = False"


def test_backup_and_restore_cycle_preserves_invariants(tmp_path):
    """Verify full backup and restoration preserves table counts, privacy invariants, and AUTO disabled."""
    # 1. Create real backup
    mgr = BackupManager(backup_dir=tmp_path)
    archive = mgr.create_full_backup()
    assert archive.exists()
    assert archive.stat().st_size > 0

    # 2. Run isolated restore validation
    validator = RestoreValidator(archive)
    result = validator.validate_restore()

    assert result.status == "PASS"
    assert result.integrity_check == "ok"
    assert result.tables_verified >= 15
    assert result.privacy_spend_preserved is True
    assert result.auto_live_disabled is True
    assert result.revoked_models_preserved is True
    assert result.rto_seconds < 1.0  # Local RTO target well under 1 second
