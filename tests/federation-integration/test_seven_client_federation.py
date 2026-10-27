"""Integration tests for 7-client federated training across IID and Non-IID partitions."""

import pytest

from fcs_pfl.orchestration.runner import FederationRunner


def test_seven_client_research_baseline_iid() -> None:
    runner = FederationRunner(job_id="test_int_research_iid")
    report = runner.run_experiment(
        profile="research",
        partition_name="iid",
        num_rounds=1,
        register_candidate=False,
    )
    assert report["status"] == "COMPLETED"
    assert report["num_rounds_completed"] == 1
    assert "accuracy" in report["eval_metrics"]
    assert len(report["tenant_breakdown"]) == 7


def test_seven_client_protected_profile_iid() -> None:
    runner = FederationRunner(job_id="test_int_protected_iid")
    report = runner.run_experiment(
        profile="protected",
        partition_name="iid",
        num_rounds=1,
        epsilon_target=2.0,
        register_candidate=True,
    )
    assert report["status"] == "COMPLETED"
    assert report["dp_enabled"] is True
    assert report["secagg_enabled"] is True
    assert report["candidate_id"] is not None


def test_seven_client_moderate_non_iid() -> None:
    runner = FederationRunner(job_id="test_int_mod_non_iid")
    report = runner.run_experiment(
        profile="research",
        partition_name="moderate_non_iid",
        num_rounds=1,
        register_candidate=False,
    )
    assert report["status"] == "COMPLETED"
    assert len(report["tenant_breakdown"]) == 7
    # Fairness metrics exist
    assert "worst_client_f1" in report["fairness_metrics"]
