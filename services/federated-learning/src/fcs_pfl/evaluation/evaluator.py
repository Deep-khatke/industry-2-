"""FCS-PFL Evaluation Engine.

Provides rigorous evaluation of global and local models against holdout test splits
and individual tenant partitions, measuring utility, fairness, and generalization.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import polars as pl
import torch
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from torch.utils.data import DataLoader, TensorDataset

from fcs_pfl.client.loader import DEPLOYABLE_FEATURES, TenantPartitionLoader
from fcs_pfl.models.mlp import TabularMLPNet

logger = logging.getLogger(__name__)

DEFAULT_TEST_SPLIT_PATH = Path("data/processed/splits/test.parquet")
DEFAULT_PREPROCESSOR_PATH = Path("data/processed/preprocessor_state.json")


class FederatedModelEvaluator:
    """Evaluates models across global holdouts and individual ISP partitions."""

    def __init__(
        self,
        test_split_path: Path = DEFAULT_TEST_SPLIT_PATH,
        preprocessor_path: Path = DEFAULT_PREPROCESSOR_PATH,
    ) -> None:
        self.test_split_path = Path(test_split_path)
        self.preprocessor_path = Path(preprocessor_path)

        # Load preprocessor state
        with open(self.preprocessor_path, "r", encoding="utf-8") as f:
            self.preprocessor = json.load(f)

        self._cached_test_data: Optional[Tuple[torch.Tensor, torch.Tensor]] = None

    def _load_global_test_data(self) -> Tuple[torch.Tensor, torch.Tensor]:
        """Load and normalize the global holdout test dataset."""
        if self._cached_test_data is None:
            if not self.test_split_path.exists():
                raise FileNotFoundError(f"Holdout test split not found: {self.test_split_path}")

            df = pl.read_parquet(self.test_split_path)
            # Filter and scale deployable features
            norm_stats = self.preprocessor.get("normalization", {})
            scaled_cols = []
            for feat in DEPLOYABLE_FEATURES:
                series = df[feat].to_numpy().astype(np.float32)
                stats = norm_stats.get(feat, {})
                mean = float(stats.get("mean", 0.0))
                std = float(stats.get("std", 1.0))
                if std < 1e-7:
                    std = 1.0
                scaled = (series - mean) / std
                scaled_cols.append(scaled)

            features = np.column_stack(scaled_cols)
            if "binary_label" in df.columns:
                labels = df["binary_label"].to_numpy().astype(np.int64)
            elif "Label" in df.columns:
                labels = df["Label"].to_numpy().astype(np.int64)
            elif "Attack" in df.columns:
                labels = df["Attack"].to_numpy().astype(np.int64)
            elif "is_attack" in df.columns:
                labels = df["is_attack"].to_numpy().astype(np.int64)
            else:
                labels = np.zeros(len(df), dtype=np.int64)

            x_tensor = torch.tensor(features, dtype=torch.float32)
            y_tensor = torch.tensor(labels, dtype=torch.long)
            self._cached_test_data = (x_tensor, y_tensor)

        return self._cached_test_data

    def evaluate_model(
        self,
        model: TabularMLPNet,
        batch_size: int = 256,
    ) -> Dict[str, Any]:
        """Evaluate model on the global holdout test set."""
        x_tensor, y_tensor = self._load_global_test_data()
        dataset = TensorDataset(x_tensor, y_tensor)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

        model.eval()
        all_preds = []
        all_probs = []
        all_targets = []

        with torch.no_grad():
            for batch_x, batch_y in loader:
                logits = model(batch_x)
                probs = torch.softmax(logits, dim=-1)[:, 1]
                preds = torch.argmax(logits, dim=-1)

                all_probs.extend(probs.cpu().numpy().tolist())
                all_preds.extend(preds.cpu().numpy().tolist())
                all_targets.extend(batch_y.cpu().numpy().tolist())

        y_true = np.array(all_targets)
        y_pred = np.array(all_preds)
        y_prob = np.array(all_probs)

        # Metrics
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)

        acc = float(np.mean(y_true == y_pred))
        prec = float(precision_score(y_true, y_pred, zero_division=0))
        rec = float(recall_score(y_true, y_pred, zero_division=0))
        f1 = float(f1_score(y_true, y_pred, zero_division=0))
        fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0

        try:
            pr_auc = float(average_precision_score(y_true, y_prob))
        except Exception:
            pr_auc = 0.0

        try:
            roc_auc = float(roc_auc_score(y_true, y_prob))
        except Exception:
            roc_auc = 0.0

        return {
            "num_test_samples": len(y_true),
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "false_positive_rate": fpr,
            "pr_auc": pr_auc,
            "roc_auc": roc_auc,
            "tp": int(tp),
            "fp": int(fp),
            "tn": int(tn),
            "fn": int(fn),
        }

    def evaluate_per_tenant(
        self,
        model: TabularMLPNet,
        partition_name: str = "iid",
        participants: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, float]]:
        """Evaluate model across each ISP tenant's validation partition."""
        p_list = participants or [f"isp_{i:02d}" for i in range(1, 8)]
        results: Dict[str, Dict[str, float]] = {}

        model.eval()
        for pid in p_list:
            loader = TenantPartitionLoader(participant_id=pid, partition_name=partition_name)
            val_x, val_y = loader.load_val_tensors()
            dataset = TensorDataset(val_x, val_y)
            dl = DataLoader(dataset, batch_size=256, shuffle=False)

            all_preds = []
            all_targets = []
            with torch.no_grad():
                for bx, by in dl:
                    logits = model(bx)
                    preds = torch.argmax(logits, dim=-1)
                    all_preds.extend(preds.cpu().numpy().tolist())
                    all_targets.extend(by.cpu().numpy().tolist())

            y_t = np.array(all_targets)
            y_p = np.array(all_preds)

            prec = float(precision_score(y_t, y_p, zero_division=0))
            rec = float(recall_score(y_t, y_p, zero_division=0))
            f1 = float(f1_score(y_t, y_p, zero_division=0))
            acc = float(np.mean(y_t == y_p)) if len(y_t) > 0 else 0.0

            results[pid] = {
                "accuracy": acc,
                "precision": prec,
                "recall": rec,
                "f1": f1,
                "samples": len(y_t),
            }

        return results

    def compute_fairness_summary(
        self,
        per_tenant_metrics: Dict[str, Dict[str, float]],
    ) -> Dict[str, float]:
        """Compute worst-client performance, mean, and variance across tenants."""
        f1_scores = [m["f1"] for m in per_tenant_metrics.values()]
        rec_scores = [m["recall"] for m in per_tenant_metrics.values()]

        return {
            "worst_client_f1": float(np.min(f1_scores)) if f1_scores else 0.0,
            "mean_client_f1": float(np.mean(f1_scores)) if f1_scores else 0.0,
            "std_client_f1": float(np.std(f1_scores)) if f1_scores else 0.0,
            "worst_client_recall": float(np.min(rec_scores)) if rec_scores else 0.0,
            "mean_client_recall": float(np.mean(rec_scores)) if rec_scores else 0.0,
        }
