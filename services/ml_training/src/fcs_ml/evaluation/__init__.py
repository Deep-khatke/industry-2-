"""Model evaluation, metrics, and robustness analysis."""

from .metrics import (
    compute_binary_metrics,
    compute_expected_calibration_error,
    compute_multiclass_metrics,
)
from .robustness import RobustnessEvaluator

__all__ = [
    "RobustnessEvaluator",
    "compute_binary_metrics",
    "compute_expected_calibration_error",
    "compute_multiclass_metrics",
]
