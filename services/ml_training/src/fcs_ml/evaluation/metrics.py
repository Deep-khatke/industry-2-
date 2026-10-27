"""Comprehensive evaluation metrics for binary and multiclass intrusion detection."""

from typing import Any

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    matthews_corrcoef,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
    roc_auc_score,
)


def compute_expected_calibration_error(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> float:
    """Calculate Expected Calibration Error (ECE) with equal-width binning."""
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    bin_indices = np.digitize(y_prob, bins) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)

    ece = 0.0
    total_samples = len(y_true)

    for i in range(n_bins):
        mask = bin_indices == i
        bin_count = np.sum(mask)
        if bin_count > 0:
            bin_acc = np.mean(y_true[mask])
            bin_conf = np.mean(y_prob[mask])
            ece += (bin_count / total_samples) * abs(bin_acc - bin_conf)

    return float(ece)


def compute_binary_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """
    Compute full suite of binary classification and operational alert metrics.
    y_prob can be 1D array of positive class probabilities or 2D array of shape (N, 2).
    """
    if y_prob.ndim == 2:
        y_score = y_prob[:, 1]
    else:
        y_score = y_prob

    y_pred = (y_score >= threshold).astype(np.int64)

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    # Rate calculations
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0

    # Area under curves (safe fallbacks if single class present in test)
    try:
        pr_auc = float(average_precision_score(y_true, y_score))
    except Exception:
        pr_auc = 0.0

    try:
        roc_auc = float(roc_auc_score(y_true, y_score))
    except Exception:
        roc_auc = 0.5

    # Probability calibration metrics
    try:
        brier = float(brier_score_loss(y_true, y_score))
    except Exception:
        brier = 0.0

    try:
        lloss = float(log_loss(y_true, y_score, eps=1e-7))
    except Exception:
        lloss = 0.0

    ece = compute_expected_calibration_error(y_true, y_score, n_bins=10)

    return {
        "pr_auc": pr_auc,
        "roc_auc": roc_auc,
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "mcc": float(matthews_corrcoef(y_true, y_pred)),
        "specificity": specificity,
        "fpr": fpr,
        "fnr": fnr,
        "brier_score": brier,
        "log_loss": lloss,
        "expected_calibration_error": ece,
        "threshold_used": float(threshold),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
        "total_samples": int(len(y_true)),
    }


def compute_multiclass_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray | None = None,
    class_names: list[str] | None = None,
) -> dict[str, Any]:
    """Compute multiclass Macro, Weighted, and per-class metrics."""
    # Convert string labels to integer indices if class_names provided
    if class_names and (isinstance(y_true[0], (str, np.str_)) if len(y_true) > 0 else False):
        name_to_idx = {name: i for i, name in enumerate(class_names)}
        y_true = np.array([name_to_idx.get(str(c), 0) for c in y_true], dtype=np.int64)

    if class_names and (isinstance(y_pred[0], (str, np.str_)) if len(y_pred) > 0 else False):
        name_to_idx = {name: i for i, name in enumerate(class_names)}
        y_pred = np.array([name_to_idx.get(str(c), 0) for c in y_pred], dtype=np.int64)

    unique_labels = sorted(set(list(y_true) + list(y_pred)))

    prec_per, rec_per, f1_per, sup_per = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=unique_labels,
        zero_division=0,
    )

    per_class_stats = {}
    for i, label_idx in enumerate(unique_labels):
        name = class_names[label_idx] if class_names and label_idx < len(class_names) else str(label_idx)
        per_class_stats[name] = {
            "precision": float(prec_per[i]),
            "recall": float(rec_per[i]),
            "f1": float(f1_per[i]),
            "support": int(sup_per[i]),
        }

    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))
    macro_prec = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    macro_rec = float(recall_score(y_true, y_pred, average="macro", zero_division=0))

    cm = confusion_matrix(y_true, y_pred, labels=unique_labels).tolist()

    res = {
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "macro_precision": macro_prec,
        "macro_recall": macro_rec,
        "per_class": per_class_stats,
        "confusion_matrix": cm,
        "num_classes": len(unique_labels),
        "total_samples": int(len(y_true)),
    }

    if y_prob is not None:
        try:
            res["log_loss"] = float(log_loss(y_true, y_prob, eps=1e-7))
        except Exception:
            res["log_loss"] = 0.0

    return res
