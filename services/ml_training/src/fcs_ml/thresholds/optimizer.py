"""Validation-only threshold optimizer for balancing detection recall and false alert burden."""

from typing import Any

import numpy as np
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score


class ThresholdOptimizer:
    """Finds optimal operational decision thresholds using validation data only."""

    def __init__(
        self,
        objective: str = "f1",
        target_fpr: float = 0.01,
        precision_floor: float = 0.90,
        n_steps: int = 100,
    ) -> None:
        self.objective = objective
        self.target_fpr = target_fpr
        self.precision_floor = precision_floor
        self.n_steps = n_steps
        self.optimal_threshold_: float = 0.5
        self.validation_metrics_: dict[str, Any] = {}

    def fit(self, y_val: np.ndarray, y_val_prob: np.ndarray) -> "ThresholdOptimizer":
        """Search validation predictions to determine optimal frozen threshold."""
        if y_val_prob.ndim == 2:
            scores = y_val_prob[:, 1]
        else:
            scores = y_val_prob

        thresholds = np.linspace(0.01, 0.99, self.n_steps)
        best_threshold = 0.5
        best_metric_val = -1.0
        best_metrics: dict[str, Any] = {}

        for th in thresholds:
            y_pred = (scores >= th).astype(np.int64)
            cm = confusion_matrix(y_val, y_pred, labels=[0, 1])
            tn, fp, fn, tp = cm.ravel()

            fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
            rec = float(recall_score(y_val, y_pred, zero_division=0))
            prec = float(precision_score(y_val, y_pred, zero_division=0))
            f1 = float(f1_score(y_val, y_pred, zero_division=0))

            if self.objective == "f1":
                if f1 > best_metric_val:
                    best_metric_val = f1
                    best_threshold = float(th)
                    best_metrics = {"f1": f1, "recall": rec, "precision": prec, "fpr": fpr}

            elif self.objective == "recall_at_fpr":
                # Must satisfy FPR <= target_fpr
                if fpr <= self.target_fpr:
                    if rec > best_metric_val:
                        best_metric_val = rec
                        best_threshold = float(th)
                        best_metrics = {"f1": f1, "recall": rec, "precision": prec, "fpr": fpr}

            elif self.objective == "precision_floor":
                # Must satisfy Precision >= precision_floor
                if prec >= self.precision_floor:
                    if rec > best_metric_val:
                        best_metric_val = rec
                        best_threshold = float(th)
                        best_metrics = {"f1": f1, "recall": rec, "precision": prec, "fpr": fpr}

        # If constrained objective couldn't be satisfied, fallback to best F1
        if best_metric_val < 0.0:
            for th in thresholds:
                y_pred = (scores >= th).astype(np.int64)
                f1 = float(f1_score(y_val, y_pred, zero_division=0))
                if f1 > best_metric_val:
                    best_metric_val = f1
                    best_threshold = float(th)
                    rec = float(recall_score(y_val, y_pred, zero_division=0))
                    prec = float(precision_score(y_val, y_pred, zero_division=0))
                    cm = confusion_matrix(y_val, y_pred, labels=[0, 1])
                    tn, fp, fn, tp = cm.ravel()
                    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
                    best_metrics = {"f1": f1, "recall": rec, "precision": prec, "fpr": fpr}

        self.optimal_threshold_ = best_threshold
        self.validation_metrics_ = {
            "objective": self.objective,
            "threshold": self.optimal_threshold_,
            "validation_f1": best_metrics.get("f1", 0.0),
            "validation_recall": best_metrics.get("recall", 0.0),
            "validation_precision": best_metrics.get("precision", 0.0),
            "validation_fpr": best_metrics.get("fpr", 0.0),
        }
        return self
