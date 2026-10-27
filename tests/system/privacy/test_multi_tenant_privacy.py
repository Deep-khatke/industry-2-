"""Multi-Tenant Privacy and Differential Privacy Verification Suite for Phase 8."""

import pytest
import sqlite3
from pathlib import Path
from fcs_pfl.privacy.accountant import PrivacyAccountant


@pytest.fixture
def temp_accountant_db(tmp_path):
    return tmp_path / "test_privacy.sqlite"


def test_seven_tenant_privacy_isolation(temp_accountant_db):
    """Verify independent privacy budget tracking across the 7 simulated ISP tenants."""
    tenants = [
        "rural-isp-alpha",
        "rural-isp-bravo",
        "rural-isp-charlie",
        "rural-isp-delta",
        "rural-isp-echo",
        "rural-isp-foxtrot",
        "rural-isp-golf",
    ]

    accountants = {t: PrivacyAccountant(tenant_id=t, db_path=temp_accountant_db, epsilon_max=10.0) for t in tenants}

    # Spend budget only on alpha and bravo
    res_a = accountants["rural-isp-alpha"].reserve_budget(round_id="rnd_01", estimated_epsilon=2.5)
    accountants["rural-isp-alpha"].commit_spend(
        reservation_id=res_a,
        spent_epsilon=2.5,
        spent_delta=1e-6,
        noise_multiplier=1.2,
        max_grad_norm=1.0,
        sample_rate=0.01,
        steps_executed=100,
        round_id="rnd_01",
    )

    res_b = accountants["rural-isp-bravo"].reserve_budget(round_id="rnd_01", estimated_epsilon=4.0)
    accountants["rural-isp-bravo"].commit_spend(
        reservation_id=res_b,
        spent_epsilon=4.0,
        spent_delta=1e-6,
        noise_multiplier=1.2,
        max_grad_norm=1.0,
        sample_rate=0.01,
        steps_executed=100,
        round_id="rnd_01",
    )

    # Verify alpha and bravo spent budget
    st_alpha = accountants["rural-isp-alpha"].get_status()
    st_bravo = accountants["rural-isp-bravo"].get_status()
    assert st_alpha["cumulative_epsilon"] == 2.5
    assert st_bravo["cumulative_epsilon"] == 4.0

    # Verify other 5 tenants remain untouched
    for t in tenants[2:]:
        st = accountants[t].get_status()
        assert st["cumulative_epsilon"] == 0.0, f"Tenant {t} privacy expenditure leaked from another tenant"


def test_privacy_budget_exhaustion(temp_accountant_db):
    """Verify accountant halts training once cumulative epsilon reaches maximum budget ceiling."""
    accountant = PrivacyAccountant(tenant_id="rural-isp-alpha", db_path=temp_accountant_db, epsilon_max=5.0)

    # Can train initially
    can_train, rem = accountant.can_train(estimated_epsilon=2.0)
    assert can_train is True
    assert rem == 5.0

    # Exhaust budget
    res_id = accountant.reserve_budget(round_id="rnd_01", estimated_epsilon=5.0)
    accountant.commit_spend(
        reservation_id=res_id,
        spent_epsilon=5.0,
        spent_delta=1e-5,
        noise_multiplier=1.0,
        max_grad_norm=1.0,
        sample_rate=0.05,
        steps_executed=200,
        round_id="rnd_01",
    )

    # Attempt further training
    can_train_now, rem_now = accountant.can_train(estimated_epsilon=0.5)
    assert can_train_now is False
    assert rem_now == 0.0
    st = accountant.get_status()
    assert st["is_exhausted"] is True


def test_conservative_privacy_accounting_on_interruption(temp_accountant_db):
    """Verify that an accountant preserves expenditure even if a subsequent round is aborted."""
    accountant = PrivacyAccountant(tenant_id="rural-isp-alpha", db_path=temp_accountant_db, epsilon_max=10.0)

    res_id = accountant.reserve_budget(round_id="rnd_01", estimated_epsilon=1.5)
    accountant.commit_spend(
        reservation_id=res_id,
        spent_epsilon=1.5,
        spent_delta=1e-6,
        noise_multiplier=1.5,
        max_grad_norm=1.0,
        sample_rate=0.01,
        steps_executed=50,
        round_id="rnd_01",
    )

    # Re-initialize accountant from disk (simulating crash / restart)
    restarted_accountant = PrivacyAccountant(tenant_id="rural-isp-alpha", db_path=temp_accountant_db, epsilon_max=10.0)
    st = restarted_accountant.get_status()
    assert st["cumulative_epsilon"] == 1.5, "Expenditure must persist across restarts without refund"

