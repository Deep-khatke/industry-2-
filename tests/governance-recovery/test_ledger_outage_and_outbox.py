"""Recovery tests for consortium ledger outage, SmartBFT quorum loss, and outbox relay."""

import pytest
from fcs_governance.contracts.models import EndorsementRecord, GovernanceOrg, ReleaseRecord
from fcs_governance.contracts.state import ReleaseState
from fcs_governance.fabric.ledger_mock import MockFabricLedger, QuorumLossError
from fcs_governance.fabric.outbox import AuditOutboxRelay
from fcs_governance.fabric.recovery import GovernanceHealth, LedgerOutageManager
from fcs_governance.workflow.integration import FCSHMDGovernanceAdapter


def test_smartbft_quorum_loss_detection(tmp_path):
    """
    Verify SmartBFT behavior:
    - 4 orderers active: Consensus OK
    - 1 orderer failure (3 active): Consensus OK (tolerates 1 failure)
    - 2 orderers failure (2 active): Quorum Lost -> QuorumLossError
    """
    db_path = str(tmp_path / "ledger_bft.db")
    ledger = MockFabricLedger(db_path=db_path)

    # 4 orderers
    assert ledger.verify_smartbft_quorum() is True

    # 1 orderer crash (orderer4)
    ledger.set_orderer_status("orderer4.fcs.net", False)
    assert ledger.get_active_orderer_count() == 3
    assert ledger.verify_smartbft_quorum() is True

    # 2 orderers crash (orderer3 and orderer4) -> quorum lost (2 < 3)
    ledger.set_orderer_status("orderer3.fcs.net", False)
    assert ledger.get_active_orderer_count() == 2
    with pytest.raises(QuorumLossError, match="SmartBFT Quorum Lost"):
        ledger.verify_smartbft_quorum()

    # Recovery
    ledger.set_orderer_status("orderer3.fcs.net", True)
    assert ledger.verify_smartbft_quorum() is True


def test_ledger_outage_detection_continuity(tmp_path):
    """
    Verify that when the consortium ledger suffers an outage:
    1. Governance health becomes DEGRADED.
    2. Promotions are frozen.
    3. Active threat detection continues with zero interruption.
    4. network_action_executed remains False permanently.
    """
    db_ledger = str(tmp_path / "ledger.db")
    db_outbox = str(tmp_path / "outbox.db")
    ledger = MockFabricLedger(db_path=db_ledger)
    outbox = AuditOutboxRelay(db_path=db_outbox, ledger=ledger)
    outage_mgr = LedgerOutageManager(ledger=ledger, outbox=outbox)
    adapter = FCSHMDGovernanceAdapter(tenant_id="isp_01")

    # Simulate outage
    outage_mgr.simulate_outage()
    health = outage_mgr.get_governance_health()

    assert health["status"] == GovernanceHealth.DEGRADED.value
    assert not outage_mgr.can_proceed_with_promotion()

    # Check that live detection status is unaffected
    det_status = adapter.get_active_model_status()
    assert det_status["network_action_executed"] is False
    assert det_status["auto_mode_enabled"] is False
    assert det_status["manual_response_mode_enforced"] is True
    assert det_status["tenant_anomaly_detector_isolated"] is True

    # Restore connectivity
    outage_mgr.restore_connectivity()
    assert outage_mgr.can_proceed_with_promotion()
