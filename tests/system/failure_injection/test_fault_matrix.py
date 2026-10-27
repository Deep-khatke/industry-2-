"""Resilience and Fault Injection Matrix Test Suite (F01–F30).

Executes all 30 controlled failure injection scenarios and asserts safe,
graceful recovery across every critical architectural component.
"""

import pytest
from tools.phase8.fault_injector.engine import FaultInjectionEngine, FaultStatus


@pytest.fixture(scope="module")
def fault_results():
    engine = FaultInjectionEngine()
    results = engine.run_all_faults()
    return {r.fault_id: r for r in results}


@pytest.mark.parametrize("fault_id", [f"F{i:02d}" for i in range(1, 31)])
def test_individual_fault_recovery(fault_results, fault_id):
    """Verify that every fault F01–F30 terminates in a PASS status."""
    assert fault_id in fault_results, f"Fault {fault_id} was not executed"
    res = fault_results[fault_id]
    assert res.status == FaultStatus.PASS, (
        f"Fault {fault_id} ({res.target}) FAILED: {res.observed_behavior} | "
        f"Residual Risk: {res.residual_risk}"
    )


def test_fault_matrix_aggregate_summary():
    """Verify aggregate resilience metrics."""
    engine = FaultInjectionEngine()
    summary = engine.run_all()
    assert summary["total_faults"] == 30
    assert summary["passed_faults"] == 30
    assert summary["failed_faults"] == 0
    assert summary["blocked_faults"] == 0
