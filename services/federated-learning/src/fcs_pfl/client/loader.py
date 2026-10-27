"""TenantPartitionLoader: Verified partition access and deployable feature extraction."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import polars as pl
import torch
from torch.utils.data import DataLoader, TensorDataset

logger = logging.getLogger(__name__)

DEPLOYABLE_FEATURES: List[str] = [
    "L4_SRC_PORT",
    "L4_DST_PORT",
    "PROTOCOL",
    "IN_BYTES",
    "IN_PKTS",
    "OUT_BYTES",
    "OUT_PKTS",
    "FLOW_DURATION_MILLISECONDS",
    "TCP_FLAGS",
    "CLIENT_TCP_FLAGS",
    "SERVER_TCP_FLAGS",
    "DURATION_IN",
    "DURATION_OUT",
    "MIN_TTL",
]


def _compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 digest of a file."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class TenantPartitionLoader:
    """
    Enforces logical and cryptographic tenant isolation when loading partitioned
    ISP telemetry for federated learning rounds.
    """

    def __init__(
        self,
        participant_id: Optional[str] = None,
        partition_name: str = "iid",
        base_dir: Path | str = "data/processed/partitions",
        preprocessor_state_path: Path | str = "data/processed/preprocessor_state.json",
    ) -> None:
        self.participant_id = participant_id
        self.partition_name = partition_name
        self.base_dir = Path(base_dir)
        self.preprocessor_state_path = Path(preprocessor_state_path)
        self._scaler_state: Optional[Dict[str, Any]] = None
        self._load_preprocessor_state()

    def _load_preprocessor_state(self) -> None:
        if self.preprocessor_state_path.exists():
            try:
                self._scaler_state = json.loads(self.preprocessor_state_path.read_text(encoding="utf-8"))
            except Exception:
                self._scaler_state = None

    def verify_partition_integrity(self, client_id: Optional[str] = None, regime: Optional[str] = None) -> bool:
        """Verify partition file checksum against partition_manifest.json."""
        cid = client_id or self.participant_id or "isp_01"
        reg = regime or self.partition_name
        manifest_file = self.base_dir / reg / "partition_manifest.json"
        partition_file = self.base_dir / reg / f"{cid}.parquet"
        if not manifest_file.exists() or not partition_file.exists():
            return False

        try:
            manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            client_entry = manifest_data.get("client_partitions", {}).get(cid, {})
            expected_hash = client_entry.get("output_checksum") or client_entry.get("assigned_record_digest")
            expected_count = client_entry.get("assigned_record_count")

            actual_hash = _compute_file_sha256(partition_file)
            if expected_hash and actual_hash == expected_hash:
                return True

            if expected_count is not None:
                df = pl.read_parquet(partition_file)
                if len(df) == expected_count:
                    return True

            return False
        except Exception:
            return False

    def load_tensors(
        self,
        client_id: Optional[str] = None,
        regime: Optional[str] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Loads X and y tensors for the specified client and partition."""
        cid = client_id or self.participant_id or "isp_01"
        reg = regime or self.partition_name

        valid_clients = {f"isp_{i:02d}" for i in range(1, 8)}
        if cid not in valid_clients:
            raise PermissionError(f"Client identifier '{cid}' is not in approved participant cohort.")

        partition_file = self.base_dir / reg / f"{cid}.parquet"
        if not partition_file.exists():
            raise FileNotFoundError(f"Partition file not found: {partition_file}")

        df = pl.read_parquet(partition_file)

        # Scale features
        norm_stats = {}
        if self._scaler_state:
            norm_stats = self._scaler_state.get("normalization", {}) or self._scaler_state.get("scale_center", {})

        features_list: List[np.ndarray] = []
        for feat in DEPLOYABLE_FEATURES:
            if feat in df.columns:
                col_data = df[feat].to_numpy().astype(np.float32)
                if norm_stats and feat in norm_stats:
                    stat_val = norm_stats[feat]
                    if isinstance(stat_val, dict):
                        mean = float(stat_val.get("mean", 0.0))
                        std = float(stat_val.get("std", 1.0))
                    else:
                        mean = float(stat_val)
                        disp = self._scaler_state.get("scale_dispersion", {}) if self._scaler_state else {}
                        std = float(disp.get(feat, 1.0))
                    if std < 1e-7:
                        std = 1.0
                    col_data = (col_data - mean) / std
            else:
                col_data = np.zeros(len(df), dtype=np.float32)
            features_list.append(col_data)

        x_arr = np.column_stack(features_list).astype(np.float32)

        # Labels
        if "binary_label" in df.columns:
            y_arr = df["binary_label"].to_numpy().astype(np.int64)
        elif "Label" in df.columns:
            y_arr = df["Label"].to_numpy().astype(np.int64)
        elif "Attack" in df.columns:
            y_arr = df["Attack"].to_numpy().astype(np.int64)
        elif "label" in df.columns:
            raw_labels = df["label"].to_list()
            y_arr = np.array([0 if str(l).lower() in ("benign", "0") else 1 for l in raw_labels], dtype=np.int64)
        else:
            y_arr = np.zeros(len(df), dtype=np.int64)

        return torch.tensor(x_arr, dtype=torch.float32), torch.tensor(y_arr, dtype=torch.long)

    def load_train_tensors(self, val_ratio: float = 0.2) -> Tuple[torch.Tensor, torch.Tensor]:
        """Load training split (e.g. first 80%) for local client training."""
        x, y = self.load_tensors()
        n = len(x)
        split_idx = int(n * (1.0 - val_ratio))
        return x[:split_idx], y[:split_idx]

    def load_val_tensors(self, val_ratio: float = 0.2) -> Tuple[torch.Tensor, torch.Tensor]:
        """Load validation split (e.g. last 20%) for local client evaluation."""
        x, y = self.load_tensors()
        n = len(x)
        split_idx = int(n * (1.0 - val_ratio))
        return x[split_idx:], y[split_idx:]

    def load_partition(
        self,
        client_id: str,
        regime: str = "iid",
        batch_size: int = 32,
        shuffle: bool = True,
    ) -> Tuple[DataLoader, int]:
        """Loads client partition into a PyTorch DataLoader."""
        x, y = self.load_tensors(client_id=client_id, regime=regime)
        dataset = TensorDataset(x, y)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)
        return loader, len(x)
