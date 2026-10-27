"""Unit tests for ModelScore v1 contract and safety invariants."""

import pytest
from pydantic import ValidationError

from packages.contracts.model_score import ModelScore, ModelType, ScoringStatus


def test_model_score_valid_creation():
    score = ModelScore(
        model_id="lightgbm_deployable_subset",
        model_type=ModelType.GENERAL_DETECTOR,
        raw_score=0.88,
        calibrated_probability=0.85,
        threshold_applied=0.5,
        prediction=1,
        predicted_label="Attack",
    )
    assert score.is_threat() is True
    assert score.network_action_executed is False
    assert score.status == ScoringStatus.SCORED


def test_model_score_probability_bounds():
    # Out of bounds probability (> 1.0 or < 0.0) should raise ValidationError
    with pytest.raises(ValidationError):
        ModelScore(
            model_id="test",
            model_type=ModelType.GENERAL_DETECTOR,
            calibrated_probability=1.5,
        )

    with pytest.raises(ValidationError):
        ModelScore(
            model_id="test",
            model_type=ModelType.GENERAL_DETECTOR,
            calibrated_probability=-0.2,
        )


def test_model_score_factories():
    missing = ModelScore.missing("spec_1", ModelType.DDOS_SPECIALIST, reason="File not found")
    assert missing.status == ScoringStatus.MISSING
    assert missing.prediction == -1
    assert missing.predicted_label == "UNKNOWN"
    assert missing.is_uncertain is True

    timeout = ModelScore.timeout("spec_2", ModelType.SCANNING_SPECIALIST, budget_us=50000.0)
    assert timeout.status == ScoringStatus.TIMEOUT
    assert timeout.latency_microseconds == 50000.0

    bypassed = ModelScore.bypassed("spec_3", ModelType.BOTNET_SPECIALIST, reason="Not routed")
    assert bypassed.status == ScoringStatus.BYPASSED
    assert bypassed.predicted_label == "BYPASSED"
