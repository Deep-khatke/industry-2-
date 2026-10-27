"""Test suite for Phase 8 Cross-Component Integration Contract Matrix (INT-01 to INT-20)."""

import pytest
from tools.phase8.compatibility_checks.contract_matrix import (
    SystemContractMatrix,
    InterfaceStatus,
)


def test_contract_matrix_completeness():
    """Verify all 20 adjacent component interfaces are defined."""
    matrix = SystemContractMatrix()
    assert len(matrix.contracts) == 20, f"Expected 20 contracts, got {len(matrix.contracts)}"
    for i in range(1, 21):
        cid = f"INT-{i:02d}"
        assert cid in matrix.contracts, f"Interface {cid} missing from contract matrix"


def test_contract_matrix_compatibility():
    """Verify that all interfaces are evaluated as COMPATIBLE in development profile."""
    matrix = SystemContractMatrix()
    res = matrix.verify_all_contracts()
    assert res["all_compatible"] is True, f"Incompatible contracts found: {res['incompatible']}"
    assert res["compatible"] == 20


@pytest.mark.parametrize("contract_id", [f"INT-{i:02d}" for i in range(1, 21)])
def test_contract_specifications(contract_id):
    """Verify contract specification metadata completeness."""
    matrix = SystemContractMatrix()
    c = matrix.contracts[contract_id]
    assert c.producer, f"{contract_id} missing producer"
    assert c.consumer, f"{contract_id} missing consumer"
    assert c.contract_version, f"{contract_id} missing contract_version"
    assert c.security_boundary, f"{contract_id} missing security_boundary"
    assert c.validation_rule, f"{contract_id} missing validation_rule"
    assert c.error_behavior, f"{contract_id} missing error_behavior"
    assert c.status == InterfaceStatus.COMPATIBLE
