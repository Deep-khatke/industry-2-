"""Unit tests for versioned federation contracts (RoundManifest, CandidateManifest, PrivacyReceipt)."""

import pytest

from fcs_pfl.contracts.manifests import (
    AggregationProtocol,
    CandidateManifest,
    CandidateStatus,
    PrivacyReceipt,
    RoundManifest,
    RoundStatus,
)


def test_round_manifest_creation_and_digest() -> None:
    manifest = RoundManifest(
        round_id="round_001",
        job_id="job_pfl_unit",
        sequence=1,
        cohort=["isp_01", "isp_02", "isp_03", "isp_04", "isp_05", "isp_06", "isp_07"],
        base_model_digest="a" * 64,
        nonce="unit_nonce_123",
    )
    digest = manifest.compute_manifest_digest()
    assert len(digest) == 64
    assert manifest.aggregation_protocol == AggregationProtocol.SECAGG_PLUS


def test_privacy_receipt_contract() -> None:
    receipt = PrivacyReceipt(
        tenant_id="isp_01",
        round_id="round_001",
        epsilon_spent=0.45,
        delta_spent=1e-5,
        cumulative_epsilon=0.45,
        cumulative_delta=1e-5,
        noise_multiplier=1.1,
        max_grad_norm=1.0,
        sample_rate=0.05,
        steps_executed=10,
        status="COMMITTED",
    )
    assert receipt.receipt_id.startswith("rcpt_")
    assert receipt.epsilon_spent == 0.45
    assert receipt.status == "COMMITTED"


def test_candidate_manifest_contract() -> None:
    candidate = CandidateManifest(
        candidate_id="fed_cand_test_01",
        round_id="round_003",
        model_family="PyTorchMLP",
        model_digest="b" * 64,
        artifact_path="artifacts/candidate-models/fed_cand_test_01/model.pt",
        feature_schema_digest="92f73ab100db06d82b252e0c86fac983083232fb247baf1cdf57afd6ba8dcbf0",
        participating_clients=["isp_01", "isp_02", "isp_03", "isp_04", "isp_05", "isp_06", "isp_07"],
        aggregation_protocol=AggregationProtocol.SECAGG_PLUS,
        status=CandidateStatus.VALIDATED,
        test_metrics={"f1": 0.88, "accuracy": 0.91},
    )
    assert candidate.status == CandidateStatus.VALIDATED
    assert candidate.aggregation_protocol == AggregationProtocol.SECAGG_PLUS
    assert candidate.test_metrics["f1"] == 0.88
