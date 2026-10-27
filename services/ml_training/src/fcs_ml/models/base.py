"""Abstract base class for all Federated Cyber Shield models."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np


class BaseFCSModel(ABC):
    """Common interface for FCS candidate models."""

    def __init__(self, model_name: str, random_seed: int = 42) -> None:
        self.model_name = model_name
        self.random_seed = random_seed
        self.is_fitted = False
        self.feature_names: list[str] = []

    @abstractmethod
    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        feature_names: list[str] | None = None,
    ) -> "BaseFCSModel":
        """Fit model on training data. X_val/y_val used strictly for early stopping / validation."""

    @abstractmethod
    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Predict discrete class labels."""

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict probability scores. Returns (N, 2) for binary or (N, C) for multiclass."""

    @abstractmethod
    def get_params(self) -> dict[str, Any]:
        """Return model hyperparameters and configuration."""

    @abstractmethod
    def save(self, filepath: Path | str) -> str:
        """Save model artifact to disk. Returns sha256 checksum of saved artifact."""

    @classmethod
    @abstractmethod
    def load(cls, filepath: Path | str) -> "BaseFCSModel":
        """Load model artifact from disk."""
