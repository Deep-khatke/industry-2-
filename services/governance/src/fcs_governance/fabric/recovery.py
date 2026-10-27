"""
Ledger Outage Handling and Recovery Management.
Enforces detection continuity, promotion freezing, and graceful reconciliation.
FCS Architecture v1.2 | Phase 7 Consortium Governance.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional

from .ledger_mock import MockFabricLedger
from .outbox import AuditOutboxRelay


class GovernanceHealth(str, Enum):
    """Health status of the consortium governance layer."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"  # Ledger unreachable; detection unaffected, promotions frozen
    CRITICAL = "CRITICAL"


class LedgerOutageManager:
    """
    Manages ledger connectivity states, outage isolation, and recovery.
    Critical Invariant: Live threat detection NEVER depends on synchronous ledger availability.
    """

    def __init__(self, ledger: MockFabricLedger, outbox: AuditOutboxRelay):
        self.ledger = ledger
        self.outbox = outbox
        self._is_outage_simulated: bool = False

    def simulate_outage(self) -> None:
        """Trigger simulated network outage to the Fabric consortium ledger."""
        self._is_outage_simulated = True
        self.ledger.is_connected = False

    def restore_connectivity(self) -> None:
        """Restore consortium ledger connectivity."""
        self._is_outage_simulated = False
        self.ledger.is_connected = True

    def get_governance_health(self) -> Dict[str, str]:
        """
        Evaluate overall governance subsystem health.
        If ledger is offline, status is DEGRADED.
        """
        if not self.ledger.is_connected:
            return {
                "status": GovernanceHealth.DEGRADED.value,
                "reason": "Consortium ledger is unreachable",
                "promotions_allowed": "FROZEN",
                "detection_engine_status": "OPERATIONAL_CONTINUITY_MAINTAINED",
                "pending_outbox_events": str(len(self.outbox.get_pending_events())),
            }

        active_orderers = self.ledger.get_active_orderer_count()
        if active_orderers < self.ledger.bft_config.quorum_size:
            return {
                "status": GovernanceHealth.DEGRADED.value,
                "reason": f"SmartBFT quorum lost ({active_orderers}/{self.ledger.bft_config.total_orderers} active)",
                "promotions_allowed": "FROZEN",
                "detection_engine_status": "OPERATIONAL_CONTINUITY_MAINTAINED",
                "pending_outbox_events": str(len(self.outbox.get_pending_events())),
            }

        return {
            "status": GovernanceHealth.HEALTHY.value,
            "reason": "All 4 consortium orderers and peers operational",
            "promotions_allowed": "ENABLED",
            "detection_engine_status": "OPERATIONAL",
            "pending_outbox_events": str(len(self.outbox.get_pending_events())),
        }

    def can_proceed_with_promotion(self) -> bool:
        """
        New model releases and promotions require active ledger commitment.
        If ledger is DEGRADED, promotions are strictly FROZEN.
        """
        health = self.get_governance_health()
        return health["status"] == GovernanceHealth.HEALTHY.value

    def reconcile_on_recovery(self) -> int:
        """
        Reconcile queued outbox events once ledger connectivity is restored.
        Returns count of reconciled transactions.
        """
        if not self.ledger.is_connected:
            return 0
        return self.outbox.reconcile_and_relay()
