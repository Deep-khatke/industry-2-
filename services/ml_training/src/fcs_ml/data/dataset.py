"""PyTorch tabular dataset wrapper and DataLoader generator."""

from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset


class TabularDataset(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    """PyTorch Dataset for tabular features and binary/multiclass target labels."""

    def __init__(self, X: np.ndarray | Any, y: np.ndarray | Any, is_multiclass: bool = False) -> None:
        if isinstance(X, np.ndarray):
            self.X = torch.tensor(X, dtype=torch.float32)
        elif torch.is_tensor(X):
            self.X = X.to(torch.float32)
        else:
            self.X = torch.tensor(np.array(X, dtype=np.float32), dtype=torch.float32)

        if is_multiclass:
            if isinstance(y, np.ndarray):
                self.y = torch.tensor(y, dtype=torch.long)
            elif torch.is_tensor(y):
                self.y = y.to(torch.long)
            else:
                self.y = torch.tensor(np.array(y, dtype=np.int64), dtype=torch.long)
        else:
            if isinstance(y, np.ndarray):
                self.y = torch.tensor(y, dtype=torch.float32).unsqueeze(1)
            elif torch.is_tensor(y):
                self.y = y.to(torch.float32).unsqueeze(1) if y.ndim == 1 else y.to(torch.float32)
            else:
                self.y = torch.tensor(np.array(y, dtype=np.float32), dtype=torch.float32).unsqueeze(1)

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.X[idx], self.y[idx]


def create_dataloader(
    X: np.ndarray,
    y: np.ndarray,
    batch_size: int = 64,
    shuffle: bool = True,
    is_multiclass: bool = False,
    num_workers: int = 0,
) -> DataLoader[Any]:
    """Factory helper to construct deterministic PyTorch DataLoader."""
    dataset = TabularDataset(X, y, is_multiclass=is_multiclass)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        drop_last=False,
    )
