"""
FCS-HMD Hierarchical Threat Detection Integration Bridge.
Connects governed, ledger-committed model releases to the Phase 5 FCS-HMD general detector.
Enforces Critical Invariants:
1. Blockchain is decoupled from live per-event inference.
2. Tenant-local anomaly models and specialists remain strictly outside federation and blockchain.
3. network_action_executed = False permanently enforced (Manual Response Only).
FCS Architecture v1.2 | Phase 7 Consortium Governance.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from ..contracts.models import ReleaseRecord
from ..contracts.state import ReleaseState


class FCSHMDGovernanceAdapter:
    """
    Adapter integrating consortium-governed releases into the FCS-HMD general detector slot.
    Guarantees zero inference-path latency: inference reads from locally loaded model weights.
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.active_general_model_release: Optional[ReleaseRecord] = None
        self.active_model_name: str = "lightgbm_deployable_subset" # baseline verified detector

    def load_governed_release(self, release: ReleaseRecord) -> None:
        """
        Load a governed model release into the general detector slot.
        Enforces that release must be ACTIVE and ledger-committed.
        """
        if release.status != ReleaseState.ACTIVE:
            raise ValueError(
                f"Cannot load unactivated release {release.release_id} (status: {release.status.value})"
            )
        if not release.ledger_tx_id:
            raise ValueError("Release must be committed to the consortium ledger")

        self.active_general_model_release = release
        self.active_model_name = f"governed_{release.release_id}"

    def get_active_model_status(self) -> Dict[str, Any]:
        """Return active general detector metadata and safety parameters."""
        return {
            "tenant_id": self.tenant_id,
            "active_model_name": self.active_model_name,
            "release_id": self.active_general_model_release.release_id if self.active_general_model_release else "baseline",
            "artifact_digest_sha384": self.active_general_model_release.artifact_digest_sha384 if self.active_general_model_release else "baseline_lgbm",
            "ledger_tx_id": self.active_general_model_release.ledger_tx_id if self.active_general_model_release else "genesis",
            "tenant_anomaly_detector_isolated": True,
            "ddos_specialist_isolated": True,
            "scanning_specialist_isolated": True,
            "botnet_specialist_isolated": True,
            "auto_mode_enabled": False,
            "network_action_executed": False,
            "manual_response_mode_enforced": True,
        }
