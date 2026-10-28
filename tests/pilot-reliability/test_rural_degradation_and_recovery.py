"""Reliability, failure recovery, and rural degradation tests for Phase 9."""

import tempfile
from pathlib import Path
import pytest

from fcs_pilot.governance.backup_recovery import BackupRecoveryManager
from fcs_pilot.operations.escalation import IncidentEscalationManager
from fcs_pilot.operations.rural_degradation import RuralNetworkSimulator


def test_rural_network_packet_loss_scenarios():
    """Verify system maintains detection continuity under 0%, 1%, 5%, and 15% stress loss."""
    results = RuralNetworkSimulator.run_all_standard_scenarios()
    assert len(results) == 5

    for res in results:
        assert res.backlog_recovered is True
        assert res.detection_continuity_maintained is True


def test_rural_exporter_reboot_sequence_handling():
    """Verify exporter reboot and sequence counter reset is handled without crash."""
    res = RuralNetworkSimulator.simulate_telemetry_stream(
        "reboot_test",
        packet_count=600,
        loss_rate_percent=1.0,
        simulate_reboot=True,
    )
    assert res.exporter_reboots_simulated == 1
    assert res.detection_continuity_maintained is True


def test_backup_and_restore_verification():
    """Verify database/state backup snapshot creation, checksum verification, and restore."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        backup_mgr = BackupRecoveryManager(Path(tmp_dir))
        state = {"tenants": ["rural-isp-alpha"], "incidents": 15, "active_rules": 3}

        # 1. Create backup
        meta = backup_mgr.create_state_backup("rural-isp-alpha", state)
        assert meta.sha256_checksum is not None
        assert Path(meta.backup_path).exists()

        # 2. Verify and restore
        restored = backup_mgr.verify_and_restore_isolated(meta)
        assert restored["integrity_verified"] is True
        assert restored["restoration_status"] == "RESTORED_CLEAN"
        assert set(restored["components_restored"]) == set(state.keys())


def test_emergency_kill_switch():
    """Verify emergency pause immediately purges rules and enters paused state."""
    esc_mgr = IncidentEscalationManager()
    pause_res = esc_mgr.trigger_emergency_pause("ciso_lead", "Suspected misconfiguration")

    assert pause_res["emergency_pause_active"] is True
    assert pause_res["status"] == "ALL_RULES_PURGED"

    resume_res = esc_mgr.resume_from_emergency_pause("ciso_lead")
    assert resume_res["emergency_pause_active"] is False
    assert resume_res["status"] == "RESUMED"
