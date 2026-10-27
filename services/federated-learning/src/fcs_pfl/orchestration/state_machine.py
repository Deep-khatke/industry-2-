"""FCS-PFL Round State Machine.

Enforces valid round state transitions, auditable timestamps, and safe abort paths.
"""

from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class RoundState(str, Enum):
    """Allowed states for an FCS-PFL training round."""

    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    ADMITTING = "ADMITTING"
    SETUP = "SETUP"
    KEY_SHARING = "KEY_SHARING"
    LOCAL_TRAINING = "LOCAL_TRAINING"
    MASKED_COLLECTION = "MASKED_COLLECTION"
    UNMASKING = "UNMASKING"
    AGGREGATE_VALIDATION = "AGGREGATE_VALIDATION"
    EVALUATING = "EVALUATING"
    CANDIDATE_READY = "CANDIDATE_READY"
    ABORTED = "ABORTED"
    FAILED = "FAILED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


# Legal state transitions
ALLOWED_TRANSITIONS: Dict[RoundState, Set[RoundState]] = {
    RoundState.CREATED: {RoundState.VALIDATING, RoundState.ABORTED, RoundState.FAILED},
    RoundState.VALIDATING: {RoundState.ADMITTING, RoundState.ABORTED, RoundState.FAILED},
    RoundState.ADMITTING: {RoundState.SETUP, RoundState.LOCAL_TRAINING, RoundState.ABORTED, RoundState.FAILED},
    # SecAgg+ branch
    RoundState.SETUP: {RoundState.KEY_SHARING, RoundState.ABORTED, RoundState.FAILED},
    RoundState.KEY_SHARING: {RoundState.LOCAL_TRAINING, RoundState.ABORTED, RoundState.FAILED},
    RoundState.LOCAL_TRAINING: {RoundState.MASKED_COLLECTION, RoundState.AGGREGATE_VALIDATION, RoundState.ABORTED, RoundState.FAILED},
    RoundState.MASKED_COLLECTION: {RoundState.UNMASKING, RoundState.ABORTED, RoundState.FAILED},
    RoundState.UNMASKING: {RoundState.AGGREGATE_VALIDATION, RoundState.ABORTED, RoundState.FAILED},
    # Common post-aggregation flow
    RoundState.AGGREGATE_VALIDATION: {RoundState.EVALUATING, RoundState.ABORTED, RoundState.FAILED},
    RoundState.EVALUATING: {RoundState.CANDIDATE_READY, RoundState.ABORTED, RoundState.FAILED},
    # Terminal or recovery states
    RoundState.CANDIDATE_READY: set(),
    RoundState.ABORTED: {RoundState.RECOVERY_REQUIRED},
    RoundState.FAILED: {RoundState.RECOVERY_REQUIRED},
    RoundState.RECOVERY_REQUIRED: {RoundState.VALIDATING, RoundState.ABORTED, RoundState.FAILED},
}


class RoundStateMachine:
    """Manages state transitions and auditable transition history for a federated round."""

    def __init__(self, round_id: str) -> None:
        self.round_id = round_id
        self.current_state = RoundState.CREATED
        self.history: List[Dict[str, Any]] = [
            {"state": self.current_state.value, "timestamp": time.time(), "reason": "Round initialized"}
        ]
        self.error_reason: Optional[str] = None

    def transition_to(self, new_state: RoundState, reason: str = "") -> bool:
        """Attempt transition to new_state. Returns True if valid, False if illegal."""
        allowed = ALLOWED_TRANSITIONS.get(self.current_state, set())
        if new_state not in allowed:
            err = f"Illegal transition from {self.current_state.value} to {new_state.value}"
            logger.error("[%s] %s", self.round_id, err)
            return False

        self.current_state = new_state
        entry = {"state": new_state.value, "timestamp": time.time(), "reason": reason}
        self.history.append(entry)
        logger.info("[%s] State -> %s (%s)", self.round_id, new_state.value, reason)
        return True

    def abort(self, reason: str) -> None:
        """Abort round unconditionally and transition to ABORTED."""
        self.error_reason = reason
        self.current_state = RoundState.ABORTED
        self.history.append({"state": RoundState.ABORTED.value, "timestamp": time.time(), "reason": reason})
        logger.warning("[%s] Round ABORTED: %s", self.round_id, reason)

    def fail(self, reason: str) -> None:
        """Fail round unconditionally and transition to FAILED."""
        self.error_reason = reason
        self.current_state = RoundState.FAILED
        self.history.append({"state": RoundState.FAILED.value, "timestamp": time.time(), "reason": reason})
        logger.error("[%s] Round FAILED: %s", self.round_id, reason)
