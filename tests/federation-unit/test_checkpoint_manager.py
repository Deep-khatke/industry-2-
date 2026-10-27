"""Unit tests for CheckpointManager safe serialization and recovery."""

from pathlib import Path
import pytest
import torch

from fcs_pfl.checkpoints.manager import CheckpointManager
from fcs_pfl.checkpoints.recovery import RecoveryManager
from fcs_pfl.models.mlp import TabularMLPNet


def test_checkpoint_save_and_load(tmp_path: Path) -> None:
    mgr = CheckpointManager(base_dir=tmp_path)
    model = TabularMLPNet(input_dim=14, hidden_dims=[32], num_classes=2)

    ckpt_dir = mgr.save_checkpoint(
        job_id="job_unit_01",
        round_id="round_1",
        model=model,
        state="CANDIDATE_READY",
        metrics={"loss": 0.35, "accuracy": 0.89},
        participants=["isp_01", "isp_02"],
    )
    assert ckpt_dir.exists()
    assert (ckpt_dir / "checkpoint_manifest.json").exists()
    assert (ckpt_dir / "global_model.pt").exists()

    # Load into new model
    model2 = TabularMLPNet(input_dim=14, hidden_dims=[32], num_classes=2)
    meta = mgr.load_checkpoint(ckpt_dir, model=model2)
    assert meta["job_id"] == "job_unit_01"
    assert meta["round_id"] == "round_1"
    assert meta["metrics"]["accuracy"] == 0.89


def test_recovery_manager_preserves_state(tmp_path: Path) -> None:
    mgr = CheckpointManager(base_dir=tmp_path)
    rec_mgr = RecoveryManager(checkpoint_manager=mgr)

    model = TabularMLPNet(input_dim=14, hidden_dims=[32], num_classes=2)
    # Check fresh job recovery
    ok, last_round, _ = rec_mgr.recover_job_state("fresh_job", model)
    assert not ok
    assert last_round is None

    # Save a checkpoint and recover
    mgr.save_checkpoint(job_id="resumed_job", round_id="round_2", model=model, state="CANDIDATE_READY")
    ok, last_round, meta = rec_mgr.recover_job_state("resumed_job", model)
    assert ok
    assert last_round == "round_2"
