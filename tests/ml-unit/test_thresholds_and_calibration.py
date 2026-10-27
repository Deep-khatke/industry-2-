"""Unit tests for ThresholdOptimizer and ProbabilityCalibrator."""

import numpy as np
import pytest

from fcs_ml.calibration.calibrator import ProbabilityCalibrator
from fcs_ml.thresholds.optimizer import ThresholdOptimizer


@pytest.mark.ml_unit
class TestThresholdsAndCalibration:
    """Validate validation-only threshold tuning and Platt/isotonic probability calibration."""

    def test_threshold_optimizer_f1(self) -> None:
        y_val = np.array([0, 0, 0, 1, 1, 1])
        y_scores = np.array([0.1, 0.2, 0.45, 0.48, 0.8, 0.9])

        opt = ThresholdOptimizer(objective="f1", n_steps=50)
        opt.fit(y_val, y_scores)

        assert 0.4 < opt.optimal_threshold_ <= 0.5
        assert opt.validation_metrics_["validation_f1"] > 0.8

    def test_threshold_optimizer_target_fpr(self) -> None:
        y_val = np.array([0, 0, 0, 1, 1, 1])
        y_scores = np.array([0.1, 0.2, 0.3, 0.6, 0.8, 0.9])

        # Target FPR = 0.0 (no false alarms allowed)
        opt = ThresholdOptimizer(objective="recall_at_fpr", target_fpr=0.01)
        opt.fit(y_val, y_scores)

        assert opt.optimal_threshold_ > 0.3
        assert opt.validation_metrics_["validation_fpr"] == 0.0

    def test_probability_calibrator_sigmoid(self) -> None:
        y_val = np.array([0, 0, 1, 1] * 10)
        # Uncalibrated raw logits / unscaled scores
        y_scores = np.array([0.2, 0.3, 0.7, 0.8] * 10)

        cal = ProbabilityCalibrator(method="sigmoid")
        cal.fit(y_val, y_scores)
        assert cal.is_fitted is True

        calibrated = cal.calibrate(np.array([0.1, 0.5, 0.9]))
        assert len(calibrated) == 3
        assert (calibrated >= 0.0).all() and (calibrated <= 1.0).all()
        assert calibrated[0] < calibrated[1] < calibrated[2]
