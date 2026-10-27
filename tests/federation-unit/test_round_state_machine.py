"""Unit tests for RoundStateMachine state transitions and abort safety."""

import pytest

from fcs_pfl.orchestration.state_machine import RoundState, RoundStateMachine


def test_round_state_machine_legal_flow() -> None:
    sm = RoundStateMachine(round_id="round_test_01")
    assert sm.current_state == RoundState.CREATED

    assert sm.transition_to(RoundState.VALIDATING, "Validating params")
    assert sm.transition_to(RoundState.ADMITTING, "Checking admission")
    assert sm.transition_to(RoundState.LOCAL_TRAINING, "Local training")
    assert sm.transition_to(RoundState.AGGREGATE_VALIDATION, "Validating aggregate")
    assert sm.transition_to(RoundState.EVALUATING, "Evaluating global candidate")
    assert sm.transition_to(RoundState.CANDIDATE_READY, "Candidate ready")
    assert sm.current_state == RoundState.CANDIDATE_READY


def test_round_state_machine_illegal_transition() -> None:
    sm = RoundStateMachine(round_id="round_test_02")
    # Illegal skip: CREATED -> CANDIDATE_READY directly
    ok = sm.transition_to(RoundState.CANDIDATE_READY, "Skipping all stages")
    assert not ok
    assert sm.current_state == RoundState.CREATED


def test_round_state_machine_abort() -> None:
    sm = RoundStateMachine(round_id="round_test_03")
    sm.transition_to(RoundState.VALIDATING)
    sm.abort("Too few active participants")
    assert sm.current_state == RoundState.ABORTED
    assert sm.error_reason == "Too few active participants"
