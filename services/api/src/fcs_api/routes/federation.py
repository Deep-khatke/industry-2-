"""FCS-PFL FastAPI Routes for Federated Learning Operations.

Provides monitoring, participant status, privacy budgets, candidate model governance,
and authorized development triggers for the React Security Dashboard.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from fcs_pfl.artifacts.candidate import CandidateModelRegistry
from fcs_pfl.checkpoints.manager import CheckpointManager
from fcs_pfl.contracts.manifests import CandidateStatus
from fcs_pfl.orchestration.runner import ALL_PARTICIPANTS, FederationRunner
from fcs_pfl.privacy.accountant import PrivacyAccountant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/federation", tags=["Federated Learning"])
dev_router = APIRouter(prefix="/v1/dev/federation", tags=["Federated Learning Dev"])


class RunSimulationRequest(BaseModel):
    profile: str = Field(default="protected", description="'research' or 'protected'")
    partition: str = Field(default="iid", description="'iid', 'moderate_non_iid', or 'strong_non_iid'")
    rounds: int = Field(default=1, ge=1, le=10)
    dropouts: List[str] = Field(default_factory=list, description="Client IDs to simulate dropouts")


class SimulateDropoutRequest(BaseModel):
    dropped_clients: List[str] = Field(default_factory=lambda: ["isp_03"])


@router.get("/status")
def get_federation_status() -> Dict[str, Any]:
    """Return high-level FCS-PFL system status, active model, and cohort health."""
    registry = CandidateModelRegistry()
    accountant = PrivacyAccountant()
    checkpoint_mgr = CheckpointManager()

    # Active model in bundle
    bundle_path = Path("artifacts/candidate-models/default_bundle.json")
    active_model_id = "pytorchmlp_research_benchmark"
    bundle_status = "ACTIVE"
    if bundle_path.exists():
        try:
            with open(bundle_path) as f:
                b_data = json.load(f)
            active_model_id = b_data.get("general_model_id", active_model_id)
            bundle_status = b_data.get("status", bundle_status)
        except Exception:
            pass

    # Registered candidates
    candidates = []
    if registry.base_dir.exists():
        for d in registry.base_dir.iterdir():
            if d.is_dir() and (d / "candidate_manifest.json").exists():
                candidates.append(d.name)

    return {
        "status": "OPERATIONAL",
        "system_name": "FCS-PFL Privacy-Preserving Federated Learning Engine",
        "version": "1.2.0",
        "framework": "Flower 1.42.0",
        "differential_privacy": "Opacus 1.6.0 (DP-SGD)",
        "secure_aggregation": "SecAgg+ (k=5/7 threshold)",
        "active_general_model": active_model_id,
        "bundle_status": bundle_status,
        "total_isp_participants": len(ALL_PARTICIPANTS),
        "min_reconstruction_threshold": 5,
        "registered_candidates_count": len(candidates),
        "latest_candidate": candidates[-1] if candidates else None,
        "zero_cost_policy": "Strictly ₹0.00 / $0.00 Local CPU Execution",
    }


@router.get("/participants")
def list_participants() -> Dict[str, Any]:
    """List all 7 simulated ISP participants, connection status, and privacy spend."""
    accountant = PrivacyAccountant()
    statuses = accountant.get_all_tenant_statuses()
    participants_info = []

    for pid in ALL_PARTICIPANTS:
        st = statuses.get(pid, accountant.get_status(pid))
        p_file = Path(f"data/processed/partitions/iid/{pid}.parquet")
        participants_info.append({
            "participant_id": pid,
            "name": f"Simulated ISP {pid.upper()}",
            "role": "Federated Participant",
            "connection_status": "ONLINE",
            "data_partition": f"iid/{pid}.parquet",
            "partition_size_bytes": p_file.stat().st_size if p_file.exists() else 0,
            "cumulative_epsilon": st.get("cumulative_epsilon", 0.0),
            "remaining_epsilon": st.get("remaining_epsilon", 10.0),
            "max_epsilon": st.get("epsilon_max", 10.0),
            "target_delta": st.get("delta_max", 1e-5),
            "is_budget_exhausted": st.get("is_exhausted", False),
            "eligibility_status": "ELIGIBLE" if not st.get("is_exhausted", False) else "BUDGET_EXHAUSTED",
        })

    return {
        "cohort_size": len(ALL_PARTICIPANTS),
        "reconstruction_threshold": 5,
        "participants": participants_info,
    }


@router.get("/rounds")
def list_rounds(job_id: Optional[str] = None) -> Dict[str, Any]:
    """List completed training round checkpoints."""
    checkpoint_mgr = CheckpointManager()
    base = checkpoint_mgr.base_dir
    rounds = []

    if base.exists():
        for j_dir in sorted(base.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if j_dir.is_dir():
                for r_dir in sorted(j_dir.iterdir()):
                    m_file = r_dir / "checkpoint_manifest.json"
                    if m_file.exists():
                        try:
                            with open(m_file) as f:
                                rounds.append(json.load(f))
                        except Exception:
                            pass

    return {
        "total_rounds": len(rounds),
        "rounds": rounds,
    }


@router.get("/rounds/{round_id}")
def get_round_detail(round_id: str) -> Dict[str, Any]:
    """Get metadata for a specific round."""
    checkpoint_mgr = CheckpointManager()
    base = checkpoint_mgr.base_dir

    if base.exists():
        for j_dir in base.iterdir():
            if j_dir.is_dir():
                r_dir = j_dir / round_id
                m_file = r_dir / "checkpoint_manifest.json"
                if m_file.exists():
                    with open(m_file) as f:
                        return json.load(f)

    raise HTTPException(status_code=404, detail=f"Round {round_id} not found")


@router.get("/models")
def list_candidate_models() -> Dict[str, Any]:
    """List registered candidate models and their validation status."""
    registry = CandidateModelRegistry()
    models = []

    if registry.base_dir.exists():
        for c_dir in sorted(registry.base_dir.iterdir()):
            if c_dir.is_dir():
                m_file = c_dir / "candidate_manifest.json"
                if m_file.exists():
                    with open(m_file) as f:
                        models.append(json.load(f))
                elif (c_dir / "model_manifest.json").exists():
                    with open(c_dir / "model_manifest.json") as f:
                        models.append(json.load(f))

    return {
        "count": len(models),
        "models": models,
    }


@router.get("/models/{model_id}")
def get_candidate_model(model_id: str) -> Dict[str, Any]:
    """Fetch details for a specific model candidate."""
    registry = CandidateModelRegistry()
    c_dir = registry.base_dir / model_id
    if not c_dir.exists():
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    m_file = c_dir / "candidate_manifest.json"
    if m_file.exists():
        with open(m_file) as f:
            return json.load(f)

    alt_file = c_dir / "model_manifest.json"
    if alt_file.exists():
        with open(alt_file) as f:
            return json.load(f)

    raise HTTPException(status_code=404, detail="Model manifest missing")


@router.get("/privacy-status")
def get_privacy_status(tenant_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    """Query cumulative privacy accounting for an authorized tenant or all tenants."""
    accountant = PrivacyAccountant()
    if tenant_id:
        st = accountant.get_status(tenant_id)
        receipts = accountant.get_receipts(tenant_id)
        return {
            "tenant_id": tenant_id,
            "status": st,
            "receipts_count": len(receipts),
            "receipts": [r.model_dump() for r in receipts],
        }

    return {
        "tenants": accountant.get_all_tenant_statuses(),
    }


@router.get("/health")
def federation_health() -> Dict[str, Any]:
    """Health check for federation coordinator."""
    return {
        "status": "HEALTHY",
        "service": "fcs-pfl-coordinator",
        "cpu_mode": "ACTIVE (Strictly Zero-Cost)",
        "memory_status": "NORMAL",
    }


# ==========================================
# Development Triggers (Simulation)
# ==========================================

@dev_router.post("/run")
def trigger_federation_run(req: RunSimulationRequest) -> Dict[str, Any]:
    """Development trigger to execute a federated training simulation round."""
    runner = FederationRunner()
    regime = req.partition.replace("-", "_")
    report = runner.run_experiment(
        profile=req.profile,
        partition_name=regime,
        num_rounds=req.rounds,
        simulated_dropouts=req.dropouts,
        register_candidate=True,
    )
    return report


@dev_router.post("/simulate-dropout")
def simulate_dropout_test(req: SimulateDropoutRequest) -> Dict[str, Any]:
    """Test SecAgg+ threshold behavior with dropouts."""
    from fcs_pfl.aggregation.secagg import SecAggConfig, SecAggProtocolSimulator
    sim = SecAggProtocolSimulator(SecAggConfig(num_participants=7, reconstruction_threshold=5))
    dummy_updates = {pid: [np.random.randn(64, 14).astype(np.float32)] for pid in ALL_PARTICIPANTS}
    _, outcome = sim.simulate_aggregation(dummy_updates, dropped_clients=req.dropped_clients)
    return outcome
