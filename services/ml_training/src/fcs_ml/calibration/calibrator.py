"""Probability calibration (Platt/Sigmoid and Isotonic) fitted strictly on validation predictions."""

from typing import Any

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from fcs_ml.evaluation.metrics import (
    compute_expected_calibration_error,
)


class ProbabilityCalibrator:
    """Calibrates model probability outputs using permitted validation scores."""

    def __init__(self, method: str = "sigmoid") -> None:
        if method not in ("sigmoid", "isotonic"):
            raise ValueError(f"Unsupported calibration method: {method}. Must be 'sigmoid' or 'isotonic'.")
        self.method = method
        self._calibrator: Any = None
        self.is_fitted = False
        self.ece_before_: float = 0.0
        self.ece_after_: float = 0.0

    def fit(self, y_val: np.ndarray, y_val_prob: np.ndarray) -> "ProbabilityCalibrator":
        """Fit calibration mapping strictly on validation probabilities."""
        if y_val_prob.ndim == 2:
            scores = y_val_prob[:, 1]
        else:
            scores = y_val_prob

        self.ece_before_ = compute_expected_calibration_error(y_val, scores)

        if self.method == "sigmoid":
            # Platt scaling: Logistic regression on log-odds / scores
            self._calibrator = LogisticRegression(C=1.0, solver="lbfgs", max_iter=200)
            self._calibrator.fit(scores.reshape(-1, 1), y_val)
        else:
            # Isotonic regression
            self._calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
            self._calibrator.fit(scores, y_val)

        calibrated_val = self.calibrate(scores)
        self.ece_after_ = compute_expected_calibration_error(y_val, calibrated_val)
        self.is_fitted = True
        return self

    def calibrate(self, y_prob: np.ndarray) -> np.ndarray:
        """Calibrate probabilities."""
        if not self.is_fitted or self._calibrator is None:
            # Fallback to uncalibrated
            return y_prob

        is_2d = y_prob.ndim == 2
        scores = y_prob[:, 1] if is_2d else y_prob

        if self.method == "sigmoid":
            cal_scores = self._calibrator.predict_proba(scores.reshape(-1, 1))[:, 1]
        else:
            cal_scores = self._calibrator.predict(scores)

        cal_scores = np.clip(cal_scores, 0.0, 1.0)
        if is_2d:
            return np.vstack([1.0 - cal_scores, cal_scores]).T
        return cal_scores

    def get_info(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "is_fitted": self.is_fitted,
            "ece_before": self.ece_before_,
            "ece_after": self.ece_after_,
        }
