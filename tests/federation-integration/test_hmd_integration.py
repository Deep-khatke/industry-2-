"""Integration tests for FCS-HMD hierarchical multi-model engine and candidate promotion."""

import json
from pathlib import Path
import pytest

from fcs_pfl.artifacts.candidate import CandidateModelRegistry
from fcs_pfl.models.mlp import TabularMLPNet


def test_candidate_promotion_preserves_specialists_and_anomaly(tmp_path: Path) -> None:
    # Create a mock bundle
    bundle_path = tmp_path / "test_bundle.json"
    initial_bundle = {
        "bundle_id": "fcs-hmd-bundle-v1",
        "general_model_id": "lightgbm_deployable_subset",
        "anomaly_model_id": "isolationforest_anomaly_tenant",
        "specialist_model_ids": ["lightgbm_ddos_specialist", "lightgbm_scanning_specialist"],
        "model_hashes": {
            "lightgbm_deployable_subset": "1" * 64,
            "isolationforest_anomaly_tenant": "2" * 64,
            "lightgbm_ddos_specialist": "3" * 64,
            "lightgbm_scanning_specialist": "4" * 64,
        },
        "bundle_digest": "initial_digest",
        "authorized_by": "security_admin",
        "status": "ACTIVE",
    }
    with open(bundle_path, "w") as f:
        json.dump(initial_bundle, f, indent=2)

    # Register a candidate
    reg = CandidateModelRegistry(base_dir=tmp_path / "candidates")
    model = TabularMLPNet(input_dim=14, hidden_dims=[32], num_classes=2)
    reg.register_candidate(
        candidate_id="fed_cand_promo_01",
        model=model,
        round_id="r3",
        job_id="j1",
        evaluation_metrics={"f1": 0.89},
    )

    # Promote candidate to bundle
    ok, err = reg.promote_candidate_to_bundle("fed_cand_promo_01", bundle_path=bundle_path)
    assert ok, f"Promotion failed: {err}"

    # Verify updated bundle
    with open(bundle_path) as f:
        updated = json.load(f)

    # Only general_model_id should have changed
    assert updated["general_model_id"] == "fed_cand_promo_01"
    # Anomaly model and specialists MUST remain untouched!
    assert updated["anomaly_model_id"] == "isolationforest_anomaly_tenant"
    assert updated["specialist_model_ids"] == ["lightgbm_ddos_specialist", "lightgbm_scanning_specialist"]
    assert "isolationforest_anomaly_tenant" in updated["model_hashes"]
