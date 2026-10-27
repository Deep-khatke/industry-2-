"""
Model Revocation and Monotonic Rollback Engine.
Enforces rollback safety invariants:
1. Target must be a previously verified compatible model.
2. Rollback manifest sequence must be strictly higher than the active model sequence.
3. Revoked models cannot be rollback targets.
4. Emergency tenant local disable works even during complete ledger outages.
FCS Architecture v1.2 | Phase 7 Consortium Governance.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..contracts.models import (
    EndorsementRecord,
    GovernanceOrg,
    ReleaseRecord,
    RevocationReason,
    RevocationRecord,
)
from ..contracts.state import ReleaseState, validate_release_transition
from ..fabric.ledger_mock import MockFabricLedger
from ..fabric.outbox import AuditOutboxRelay


class RollbackSecurityError(Exception):
    """Raised when a rollback violates security or integrity rules."""
    pass


class ModelRollbackEngine:
    """Manages secure rollbacks and formal model revocations."""

    def __init__(self, ledger: MockFabricLedger, outbox: AuditOutboxRelay):
        self.ledger = ledger
        self.outbox = outbox

    def revoke_release(
        self,
        release: ReleaseRecord,
        revoking_org: GovernanceOrg,
        revoker_identity: str,
        reason: RevocationReason,
        details: str,
        endorsements: List[EndorsementRecord],
    ) -> RevocationRecord:
        """Revoke a release on ledger and mark local record as REVOKED."""
        revocation_id = f"rev-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        rev_digest = hashlib.sha384(
            f"{revocation_id}:{release.release_id}:{reason.value}:{details}".encode()
        ).hexdigest()

        revocation = RevocationRecord(
            revocation_id=revocation_id,
            target_release_id=release.release_id,
            revoked_by_org=revoking_org,
            revoker_identity=revoker_identity,
            reason=reason,
            details=details,
            authorization_reference="EMERGENCY_CONSORTIUM_REVOCATION_ORDER",
            revocation_digest_sha384=rev_digest,
            timestamp=now,
        )

        # Enqueue in outbox
        outbox_event = self.outbox.enqueue_event(
            event_type="REVOCATION",
            aggregate_id=revocation_id,
            payload=revocation.model_dump(),
        )

        # Submit to Fabric ledger
        tx_id = self.ledger.record_revocation(revocation, endorsements)
        revocation.ledger_tx_id = tx_id
        self.outbox.mark_committed(outbox_event.event_id, tx_id)

        # Transition local state
        validate_release_transition(release.status, ReleaseState.REVOKED)
        release.status = ReleaseState.REVOKED

        return revocation

    def execute_monotonic_rollback(
        self,
        active_release: ReleaseRecord,
        target_rollback_release: ReleaseRecord,
        current_sequence: int,
        rollback_sequence: int,
    ) -> ReleaseRecord:
        """
        Execute an approved rollback from active_release to target_rollback_release.
        Enforces monotonic sequence increment and non-revoked target.
        """
        # 1. Monotonic sequence check: Rollback manifest sequence MUST be strictly greater
        if rollback_sequence <= current_sequence:
            raise RollbackSecurityError(
                f"Monotonic sequence violation: rollback sequence ({rollback_sequence}) "
                f"must be strictly greater than current active sequence ({current_sequence})."
            )

        # 2. Target must not be revoked
        if target_rollback_release.status == ReleaseState.REVOKED:
            raise RollbackSecurityError(
                f"Cannot rollback to revoked model release: {target_rollback_release.release_id}"
            )

        # 3. Target must have been previously verified / committed
        on_chain = self.ledger.query_release(target_rollback_release.release_id)
        if not on_chain or on_chain.get("is_revoked"):
            raise RollbackSecurityError(
                f"Rollback target {target_rollback_release.release_id} is not a valid non-revoked ledger asset"
            )

        # Transition active model to ROLLED_BACK
        validate_release_transition(active_release.status, ReleaseState.ROLLED_BACK)
        active_release.status = ReleaseState.ROLLED_BACK

        # Activate target model
        target_rollback_release.status = ReleaseState.ACTIVE
        return target_rollback_release

    def emergency_tenant_local_disable(self, tenant_id: str, active_release: ReleaseRecord) -> None:
        """
        Emergency local model disable executed by tenant.
        Operates locally even during total blockchain ledger failure.
        """
        # Revert active release to ELIGIBLE_FOR_ACTIVATION or ROLLED_BACK locally
        active_release.status = ReleaseState.ROLLED_BACK
