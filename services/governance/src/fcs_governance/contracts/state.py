"""
Release Lifecycle States and State Machine Transitions.
FCS Architecture v1.2 | Phase 7 Consortium Governance.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Set


class ReleaseState(str, Enum):
    """
    The 12 formal release states defined by Architecture v1.2.
    Every state transition must be strictly authorized and auditable.
    """
    CANDIDATE = "CANDIDATE"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    SIGNING_PENDING = "SIGNING_PENDING"
    SIGNED = "SIGNED"
    LEDGER_PENDING = "LEDGER_PENDING"
    LEDGER_COMMITTED = "LEDGER_COMMITTED"
    ELIGIBLE_FOR_ACTIVATION = "ELIGIBLE_FOR_ACTIVATION"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"
    ROLLED_BACK = "ROLLED_BACK"


# Valid transition graph
VALID_RELEASE_TRANSITIONS: Dict[ReleaseState, Set[ReleaseState]] = {
    ReleaseState.CANDIDATE: {ReleaseState.UNDER_REVIEW, ReleaseState.REJECTED},
    ReleaseState.UNDER_REVIEW: {ReleaseState.APPROVED, ReleaseState.REJECTED},
    ReleaseState.APPROVED: {ReleaseState.SIGNING_PENDING, ReleaseState.REJECTED},
    ReleaseState.SIGNING_PENDING: {ReleaseState.SIGNED, ReleaseState.REJECTED},
    ReleaseState.SIGNED: {ReleaseState.LEDGER_PENDING, ReleaseState.REJECTED},
    ReleaseState.LEDGER_PENDING: {ReleaseState.LEDGER_COMMITTED, ReleaseState.REJECTED},
    ReleaseState.LEDGER_COMMITTED: {ReleaseState.ELIGIBLE_FOR_ACTIVATION, ReleaseState.REVOKED},
    ReleaseState.ELIGIBLE_FOR_ACTIVATION: {ReleaseState.ACTIVE, ReleaseState.REVOKED},
    ReleaseState.ACTIVE: {ReleaseState.ROLLED_BACK, ReleaseState.REVOKED},
    ReleaseState.REJECTED: set(),   # Terminal
    ReleaseState.REVOKED: set(),    # Terminal for this specific release
    ReleaseState.ROLLED_BACK: set(), # Terminal (superseded by previous release)
}


class InvalidStateTransitionError(Exception):
    """Raised when an illegal release state transition is attempted."""
    pass


def validate_release_transition(from_state: ReleaseState, to_state: ReleaseState) -> None:
    """Validate that transition from from_state to to_state is allowed."""
    allowed = VALID_RELEASE_TRANSITIONS.get(from_state, set())
    if to_state not in allowed:
        raise InvalidStateTransitionError(
            f"Illegal release state transition: {from_state.value} -> {to_state.value}. "
            f"Allowed transitions: {[s.value for s in allowed]}"
        )
