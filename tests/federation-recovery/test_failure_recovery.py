"""Recovery tests: round interruption, active model preservation, checkpoint recovery."""

from pathlib import Path
import pytest

from fcs_pfl.artifacts.candidate import CandidateModelRegistry
from fcs_pfl.checkpoints.manager import CheckpointManager
from fcs_pfl.checkpoints.recovery import RecoveryManager
from fcs_pfl.models.mlp import TabularMLPNet
from fcs_pfl.orchestration.runner import FederationRunner


def test_interrupted_round_preserves_active_detector() -> None:
    bundle_path = Path("artifacts/candidate-models/default_bundle.json")
    if not bundle_path.exists():
        pytest.skip("default_bundle.json not present")

    from fcs_pfl.client.loader import _compute_file_sha256
    before_hash = _compute_file_sha256(bundle_path)

    # Run a simulation round with excessive dropouts (3 dropped -> abort)
    runner = FederationRunner(job_id="test_abort_job")
    report = runner.run_experiment(
        profile="research",
        num_rounds=1,
        simulated_dropouts=["isp_01", "isp_02", "isp_03"],
        register_candidate=True,
    )
    assert report["status"] == "ABORTED"

    # Verify active bundle file was untouched
    after_hash = _compute_file_sha256(bundle_path)
    assert before_hash == after_hash


def test_checkpoint_reconciliation_on_crash(tmp_path: Path) -> None:
    ckpt_mgr = CheckpointManager(base_dir=tmp_path)
    rec_mgr = RecoveryManager(checkpoint_manager=ckpt_mgr)

    model = TabularMLPNet(input_dim=14, hidden_dims=[32], num_classes=2)

    # Save a FAILED round checkpoint
    ckpt_mgr.save_checkpoint(job_id="crash_job", round_id="round_1", model=model, state="FAILED")

    recovered, round_id, meta = rec_mgr.recover_job_state("crash_job", model)
    assert recovered
    assert meta["state"] == "FAILED"
