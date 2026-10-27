"""Unit tests for binary and multiclass evaluation metrics."""

import numpy as np
import pytest

from fcs_ml.evaluation.metrics import (
    compute_binary_metrics,
    compute_expected_calibration_error,
    compute_multiclass_metrics,
)


@pytest.mark.ml_unit
class TestEvaluationMetrics:
    """Validate calculation of PR-AUC, ROC-AUC, F1, ECE, and confusion matrix."""

    def test_binary_metrics_perfect_classifier(self) -> None:
        y_true = np.array([0, 0, 1, 1])
        y_prob = np.array([0.05, 0.10, 0.90, 0.95])
        m = compute_binary_metrics(y_true, y_prob, threshold=0.5)

        assert m["f1"] == 1.0
        assert m["precision"] == 1.0
        assert m["recall"] == 1.0
        assert m["pr_auc"] == 1.0
        assert m["roc_auc"] == 1.0
        assert m["fpr"] == 0.0
        assert m["fnr"] == 0.0
        assert m["confusion_matrix"]["tp"] == 2
        assert m["confusion_matrix"]["tn"] == 2

    def test_expected_calibration_error(self) -> None:
        y_true = np.array([1, 1, 0, 0])
        # Well-calibrated probabilities
        y_prob = np.array([0.9, 0.9, 0.1, 0.1])
        ece = compute_expected_calibration_error(y_true, y_prob, n_bins=5)
        assert ece >= 0.0
        assert ece < 0.20

    def test_multiclass_metrics(self) -> None:
        y_true = np.array([0, 1, 2, 0, 1, 2])
        y_pred = np.array([0, 1, 2, 0, 1, 1])  # 5/6 correct
        class_names = ["Benign", "DoS", "DDoS"]

        m = compute_multiclass_metrics(y_true, y_pred, class_names=class_names)
        assert m["num_classes"] == 3
        assert "macro_f1" in m
        assert "weighted_f1" in m
        assert "Benign" in m["per_class"]
        assert m["per_class"]["Benign"]["recall"] == 1.0
