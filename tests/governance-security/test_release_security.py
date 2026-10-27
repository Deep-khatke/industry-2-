"""Security tests for release state governance, rollback validation, and model promotion."""

import pytest
from fcs_governance.contracts.models import GovernanceOrg, ReleaseRecord, RevocationReason
from fcs_governance.contracts.state import InvalidStateTransitionError, ReleaseState
from fcs_governance.crypto.dual_signer import DualSigner
from fcs_governance.fabric.ledger_mock import MockFabricLedger
from fcs_governance.fabric.outbox import AuditOutboxRelay
from fcs_governance.workflow.rollback import ModelRollbackEngine, RollbackSecurityError


def test_illegal_state_transition_blocked():
    """Verify that jumping states (e.g. CANDIDATE -> ACTIVE directly) is blocked."""
    from fcs_governance.contracts.state import validate_release_transition
    with pytest.raises(InvalidStateTransitionError, match="Illegal release state transition"):
        validate_release_transition(ReleaseState.CANDIDATE, ReleaseState.ACTIVE)


def test_rollback_requires_strictly_higher_sequence(tmp_path):
    """Verify rollback cannot use equal or lower manifest sequence (anti-replay/anti-downgrade)."""
    db_ledger = str(tmp_path / "ledger.db")
    db_outbox = str(tmp_path / "outbox.db")
    ledger = MockFabricLedger(db_path=db_ledger)
    outbox = AuditOutboxRelay(db_path=db_outbox, ledger=ledger)
    engine = ModelRollbackEngine(ledger=ledger, outbox=outbox)

    active_release = ReleaseRecord(
        release_id="rel-active-v2",
        manifest_digest_sha384="sha384-v2",
        artifact_digest_sha384="art-v2",
        evaluation_digest="eval-v2",
        policy_version="1.2.0",
        model_lineage_ref="lineage-v2",
        status=ReleaseState.ACTIVE,
    )

    prior_release = ReleaseRecord(
        release_id="rel-prior-v1",
        manifest_digest_sha384="sha384-v1",
        artifact_digest_sha384="art-v1",
        evaluation_digest="eval-v1",
        policy_version="1.2.0",
        model_lineage_ref="lineage-v1",
        status=ReleaseState.LEDGER_COMMITTED,
    )

    # Rollback with sequence 2 <= current sequence 2 must fail
    with pytest.raises(RollbackSecurityError, match="Monotonic sequence violation"):
        engine.execute_monotonic_rollback(
            active_release=active_release,
            target_rollback_release=prior_release,
            current_sequence=2,
            rollback_sequence=2,
        )


def test_rollback_to_revoked_release_blocked(tmp_path):
    """Verify rollback to a revoked release is blocked."""
    db_ledger = str(tmp_path / "ledger.db")
    db_outbox = str(tmp_path / "outbox.db")
    ledger = MockFabricLedger(db_path=db_ledger)
    outbox = AuditOutboxRelay(db_path=db_outbox, ledger=ledger)
    engine = ModelRollbackEngine(ledger=ledger, outbox=outbox)

    active_release = ReleaseRecord(
        release_id="rel-active-v2",
        manifest_digest_sha384="sha384-v2",
        artifact_digest_sha384="art-v2",
        evaluation_digest="eval-v2",
        policy_version="1.2.0",
        model_lineage_ref="lineage-v2",
        status=ReleaseState.ACTIVE,
    )

    revoked_release = ReleaseRecord(
        release_id="rel-revoked-v1",
        manifest_digest_sha384="sha384-v1",
        artifact_digest_sha384="art-v1",
        evaluation_digest="eval-v1",
        policy_version="1.2.0",
        model_lineage_ref="lineage-v1",
        status=ReleaseState.REVOKED,
    )

    with pytest.raises(RollbackSecurityError, match="Cannot rollback to revoked model release"):
        engine.execute_monotonic_rollback(
            active_release=active_release,
            target_rollback_release=revoked_release,
            current_sequence=2,
            rollback_sequence=3,
        )
