"""Unit tests for PrivacyAccountant persistent SQLite state machine and budget exhaustion."""

from pathlib import Path
import pytest

from fcs_pfl.privacy.accountant import PrivacyAccountant, PrivacyBudgetExhaustedError


def test_accountant_persistence_and_spend(tmp_path: Path) -> None:
    db_file = tmp_path / "test_budget.sqlite"
    acc = PrivacyAccountant(tenant_id="isp_01", db_path=db_file, epsilon_max=5.0)

    # Initial state
    st = acc.get_status()
    assert st["cumulative_epsilon"] == 0.0
    assert st["remaining_epsilon"] == 5.0
    assert not st["is_exhausted"]

    # Reserve & Commit Spend
    res_id = acc.reserve_budget(round_id="round_1", estimated_epsilon=1.0, target_delta=1e-5)
    assert res_id.startswith("res_")

    receipt = acc.commit_spend(reservation_id=res_id, spent_epsilon=1.2, spent_delta=1e-5, round_id="round_1")
    assert receipt.cumulative_epsilon == 1.2
    assert receipt.status == "COMMITTED"

    # Simulate crash and restart: create a new accountant instance on the same SQLite DB
    acc2 = PrivacyAccountant(tenant_id="isp_01", db_path=db_file, epsilon_max=5.0)
    st2 = acc2.get_status()
    assert st2["cumulative_epsilon"] == 1.2
    assert abs(st2["remaining_epsilon"] - 3.8) < 1e-5


def test_accountant_budget_exhaustion(tmp_path: Path) -> None:
    db_file = tmp_path / "test_exhaust.sqlite"
    acc = PrivacyAccountant(tenant_id="isp_02", db_path=db_file, epsilon_max=2.0)

    # Spend 1.5 eps
    res_id = acc.reserve_budget(round_id="r1", estimated_epsilon=1.5, target_delta=1e-5)
    acc.commit_spend(reservation_id=res_id, spent_epsilon=1.5, spent_delta=1e-5, round_id="r1")

    # Attempt to reserve 1.0 eps (1.5 + 1.0 = 2.5 > 2.0 max) -> MUST fail closed!
    with pytest.raises(PrivacyBudgetExhaustedError):
        acc.reserve_budget(round_id="r2", estimated_epsilon=1.0, target_delta=1e-5)

    # can_train should return False
    can_train, rem = acc.can_train(participant_id="isp_02", estimated_epsilon=1.0)
    assert not can_train
    assert rem == 0.5
