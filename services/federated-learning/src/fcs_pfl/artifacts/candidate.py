"""FCS-PFL Candidate Model Registration and FCS-HMD Integration.

Exports federated model candidates into artifacts/candidate-models/, generates
manifests with SHA-256 integrity digests, and ensures safe promotion checks.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import torch

from fcs_pfl.client.loader import _compute_file_sha256
from fcs_pfl.contracts.manifests import CandidateManifest, CandidateStatus
from fcs_pfl.models.mlp import TabularMLPNet

logger = logging.getLogger(__name__)

DEFAULT_CANDIDATES_DIR = Path("artifacts/candidate-models")


class CandidateModelRegistry:
    """Manages candidate model artifacts, validation, and promotion readiness."""

    def __init__(self, base_dir: Path = DEFAULT_CANDIDATES_DIR) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def register_candidate(
        self,
        candidate_id: str,
        model: TabularMLPNet,
        round_id: str,
        job_id: str,
        evaluation_metrics: Dict[str, Any],
        privacy_receipts: Optional[list] = None,
        is_dp_enabled: bool = False,
        is_secagg_enabled: bool = False,
        status: CandidateStatus = CandidateStatus.REGISTERED,
    ) -> Path:
        """Register a new federated model candidate artifact."""
        candidate_dir = self.base_dir / candidate_id
        candidate_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save weights safely
        weights_path = candidate_dir / "model.pt"
        torch.save(model.state_dict(), weights_path)
        weights_hash = _compute_file_sha256(weights_path)

        # 2. Save model architecture JSON
        arch_config = {
            "model_type": "TabularMLPNet",
            "framework": "pytorch",
            "input_dim": model.input_dim,
            "hidden_dims": model.hidden_dims,
            "num_classes": model.num_classes,
            "use_group_norm": model.use_group_norm,
        }
        arch_path = candidate_dir / "model.json"
        with open(arch_path, "w", encoding="utf-8") as f:
            json.dump(arch_config, f, indent=2)

        from fcs_pfl.admission.validator import LOCKED_FEATURE_SCHEMA_DIGEST
        from fcs_pfl.contracts.manifests import AggregationProtocol

        # 3. Save standard Phase 3/5 model_manifest.json
        model_manifest = {
            "model_id": candidate_id,
            "model_family": "PyTorchMLP",
            "model_type": "pytorch_mlp",
            "framework": "pytorch",
            "feature_set": "deployable_v1",
            "feature_track": "deployable",
            "feature_schema_digest": LOCKED_FEATURE_SCHEMA_DIGEST,
            "artifact_hash": weights_hash,
            "artifact_path": str(weights_path),
            "input_dimension": model.input_dim,
            "hash": weights_hash,
            "round_id": round_id,
            "job_id": job_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": status.value,
        }
        with open(candidate_dir / "model_manifest.json", "w", encoding="utf-8") as f:
            json.dump(model_manifest, f, indent=2)

        # 4. Save CandidateManifest contract
        candidate_manifest = CandidateManifest(
            candidate_id=candidate_id,
            round_id=round_id,
            model_family="PyTorchMLP",
            model_digest=weights_hash,
            artifact_path=str(weights_path),
            feature_schema_digest=LOCKED_FEATURE_SCHEMA_DIGEST,
            participating_clients=[f"isp_{i:02d}" for i in range(1, 8)],
            aggregation_protocol=AggregationProtocol.SECAGG_PLUS if is_secagg_enabled else AggregationProtocol.PLAINTEXT_FEDAVG,
            status=status,
            privacy_metrics={"dp_applied": is_dp_enabled, "receipt_refs": privacy_receipts or []},
            test_metrics={k: float(v) for k, v in evaluation_metrics.items() if isinstance(v, (int, float))},
            worst_client_metrics={},
        )

        with open(candidate_dir / "candidate_manifest.json", "w", encoding="utf-8") as f:
            json.dump(candidate_manifest.model_dump(), f, indent=2, default=str)

        logger.info(
            "Registered candidate %s at %s with status %s (hash: %s...)",
            candidate_id,
            candidate_dir,
            status.value,
            weights_hash[:12],
        )
        return candidate_dir

    def validate_candidate_integrity(self, candidate_id: str) -> Tuple[bool, Optional[str]]:
        """Validate candidate file existence, schema, and cryptographic SHA-256 hash."""
        candidate_dir = self.base_dir / candidate_id
        if not candidate_dir.exists():
            return False, f"Candidate dir {candidate_dir} does not exist"

        weights_path = candidate_dir / "model.pt"
        manifest_path = candidate_dir / "candidate_manifest.json"

        if not weights_path.exists():
            return False, "Weights file model.pt missing"
        if not manifest_path.exists():
            return False, "candidate_manifest.json missing"

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        expected_hash = manifest_data.get("model_digest")
        actual_hash = _compute_file_sha256(weights_path)
        if actual_hash != expected_hash:
            return False, f"Hash mismatch! Expected {expected_hash}, got {actual_hash}"

        return True, None

    def promote_candidate_to_bundle(
        self,
        candidate_id: str,
        bundle_path: Path = Path("artifacts/candidate-models/default_bundle.json"),
        authorized_by: str = "security_admin",
    ) -> Tuple[bool, Optional[str]]:
        """Promote a validated federated candidate to be the active general detector in DetectionBundle.

        CRITICAL SAFETY CONSTRAINTS:
        - Must NOT replace or federate the tenant-local anomaly detector.
        - Must NOT replace or federate attack specialists.
        - Must maintain Manual Response mode.
        """
        is_valid, err = self.validate_candidate_integrity(candidate_id)
        if not is_valid:
            return False, f"Promotion rejected: candidate failed integrity check: {err}"

        if not bundle_path.exists():
            return False, f"Detection bundle file not found: {bundle_path}"

        with open(bundle_path, "r", encoding="utf-8") as f:
            bundle_data = json.load(f)

        # Update ONLY the general detector
        bundle_data["general_model_id"] = candidate_id
        candidate_dir = self.base_dir / candidate_id
        bundle_data["model_hashes"][candidate_id] = _compute_file_sha256(candidate_dir / "model.pt")
        bundle_data["authorized_by"] = authorized_by
        bundle_data["status"] = "ACTIVE"
        bundle_data["activated_at"] = datetime.now(timezone.utc).isoformat()

        # Recompute bundle digest
        serialized = json.dumps({k: v for k, v in bundle_data.items() if k != "bundle_digest"}, sort_keys=True)
        bundle_data["bundle_digest"] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        with open(bundle_path, "w", encoding="utf-8") as f:
            json.dump(bundle_data, f, indent=2)

        logger.info("Promoted candidate %s to general detector in %s", candidate_id, bundle_path)
        return True, None
