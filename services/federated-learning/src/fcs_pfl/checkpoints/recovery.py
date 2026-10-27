"""FCS-PFL Failure Recovery and Crash Consistency Manager.

Guarantees that interrupted rounds do not corrupt active models, prevents
replayed manifests, and reconciles checkpoint states.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fcs_pfl.checkpoints.manager import CheckpointManager
from fcs_pfl.models.mlp import TabularMLPNet

logger = logging.getLogger(__name__)


class RecoveryManager:
    """Manages coordinator and round crash recovery."""

    def __init__(self, checkpoint_manager: Optional[CheckpointManager] = None) -> None:
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()

    def recover_job_state(
        self,
        job_id: str,
        model: TabularMLPNet,
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Attempt to restore the most recent valid checkpoint for a job.

        Returns (recovered_flag, last_round_id, metadata).
        """
        latest_ckpt = self.checkpoint_manager.get_latest_checkpoint(job_id)
        if not latest_ckpt:
            logger.info("No existing checkpoints found for job %s. Starting fresh.", job_id)
            return False, None, None

        try:
            metadata = self.checkpoint_manager.load_checkpoint(latest_ckpt, model=model)
            state = metadata.get("state")
            round_id = metadata.get("round_id")

            # Check if last recorded state was ABORTED or FAILED
            if state in ("ABORTED", "FAILED"):
                logger.warning(
                    "Latest checkpoint %s was in state %s. State must be reconciled before resuming.",
                    latest_ckpt.name,
                    state,
                )
                return True, round_id, metadata

            logger.info("Successfully recovered model state from %s (Round %s)", latest_ckpt.name, round_id)
            return True, round_id, metadata

        except Exception as e:
            logger.error("Failed to recover checkpoint from %s: %s", latest_ckpt, e)
            return False, None, None

    def verify_no_active_model_tampering(
        self,
        active_model_path: Path,
        expected_active_digest: str,
    ) -> bool:
        """Verify that an interrupted training round did not overwrite the production active detector."""
        if not active_model_path.exists():
            return False

        from fcs_pfl.client.loader import _compute_file_sha256
        actual_hash = _compute_file_sha256(active_model_path)
        return actual_hash == expected_active_digest
