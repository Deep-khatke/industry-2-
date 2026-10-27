"""FCS-PFL Checkpoint Manager.

Manages durable, safe serialization of training round state, model weights,
and cryptographic digests without unpickling arbitrary executable objects.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch

from fcs_pfl.models.mlp import TabularMLPNet

logger = logging.getLogger(__name__)

DEFAULT_CHECKPOINT_DIR = Path("artifacts/federation/checkpoints")


class CheckpointManager:
    """Manages persistent round checkpoints for FCS-PFL."""

    def __init__(self, base_dir: Path = DEFAULT_CHECKPOINT_DIR) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(
        self,
        job_id: str,
        round_id: str,
        model: TabularMLPNet,
        state: str,
        metrics: Optional[Dict[str, Any]] = None,
        participants: Optional[List[str]] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Persist model weights and metadata for a completed round."""
        ckpt_dir = self.base_dir / job_id / round_id
        ckpt_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save model weights safely (PyTorch state_dict only)
        weights_path = ckpt_dir / "global_model.pt"
        torch.save(model.state_dict(), weights_path)

        # 2. Compute digest
        model_digest = model.compute_model_digest()

        # 3. Save structured metadata
        metadata = {
            "job_id": job_id,
            "round_id": round_id,
            "state": state,
            "model_digest": model_digest,
            "weights_file": "global_model.pt",
            "participants": participants or [],
            "metrics": metrics or {},
            "extra_metadata": extra_metadata or {},
        }

        manifest_path = ckpt_dir / "checkpoint_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info("Saved checkpoint for %s/%s at %s", job_id, round_id, ckpt_dir)
        return ckpt_dir

    def load_checkpoint(
        self,
        checkpoint_dir: Path,
        model: Optional[TabularMLPNet] = None,
    ) -> Dict[str, Any]:
        """Load checkpoint metadata and optionally populate model weights."""
        ckpt_dir = Path(checkpoint_dir)
        manifest_path = ckpt_dir / "checkpoint_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Checkpoint manifest missing in {ckpt_dir}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        weights_path = ckpt_dir / metadata.get("weights_file", "global_model.pt")
        if not weights_path.exists():
            raise FileNotFoundError(f"Weights file missing: {weights_path}")

        if model is not None:
            state_dict = torch.load(weights_path, map_location="cpu", weights_only=True)
            model.load_state_dict(state_dict)
            model.eval()

        return metadata

    def list_checkpoints(self, job_id: str) -> List[Path]:
        """List all checkpoint directories for a given job ordered by creation."""
        job_dir = self.base_dir / job_id
        if not job_dir.exists():
            return []
        subdirs = [p for p in job_dir.iterdir() if p.is_dir()]
        return sorted(subdirs, key=lambda p: os.path.getmtime(p))

    def get_latest_checkpoint(self, job_id: str) -> Optional[Path]:
        """Return the latest checkpoint directory for a job if available."""
        ckpts = self.list_checkpoints(job_id)
        return ckpts[-1] if ckpts else None
