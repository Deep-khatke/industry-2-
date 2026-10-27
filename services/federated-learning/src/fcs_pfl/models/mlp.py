"""Shared PyTorch TabularMLPNet and parameter serialization helpers for Flower."""

from __future__ import annotations

import hashlib
from typing import Any, List, Optional

import numpy as np
import torch
import torch.nn as nn


class TabularMLPNet(nn.Module):
    """
    Deterministic PyTorch Multi-Layer Perceptron for 14-dim deployable NetFlow features.
    Configurable for standard BatchNorm or Opacus-compatible GroupNorm.
    """

    def __init__(
        self,
        input_dim: int = 14,
        hidden_dims: Optional[List[int]] = None,
        output_dim: int = 2,
        num_classes: Optional[int] = None,
        dropout_rate: float = 0.2,
        use_group_norm: bool = False,
        use_batch_norm: bool = True,
    ) -> None:
        super().__init__()
        if num_classes is not None:
            output_dim = num_classes

        hidden_dims = hidden_dims or [64, 32]
        layers: List[nn.Module] = []

        prev_dim = input_dim
        for h_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, h_dim))
            if use_group_norm:
                # Opacus-compatible normalization (does not couple sample statistics)
                num_groups = min(16, h_dim)
                layers.append(nn.GroupNorm(num_groups=num_groups, num_channels=h_dim))
            elif use_batch_norm:
                layers.append(nn.BatchNorm1d(h_dim))
            layers.append(nn.ReLU())
            if dropout_rate > 0.0:
                layers.append(nn.Dropout(dropout_rate))
            prev_dim = h_dim

        layers.append(nn.Linear(prev_dim, output_dim))
        self.network = nn.Sequential(*layers)
        self.input_dim = input_dim
        self.hidden_dims = hidden_dims
        self.output_dim = output_dim
        self.num_classes = output_dim
        self.use_group_norm = use_group_norm

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)

    def get_parameter_count(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def get_parameters(self) -> List[np.ndarray]:
        """Extract ordered parameter tensors as NumPy ndarrays for Flower transmission."""
        return [val.cpu().numpy() for _, val in self.state_dict().items()]

    def set_parameters(self, parameters: List[np.ndarray]) -> None:
        """Restore parameter tensors from Flower ndarrays into PyTorch state_dict."""
        params_dict = zip(self.state_dict().keys(), parameters, strict=True)
        state_dict = {k: torch.tensor(v) for k, v in params_dict}
        self.load_state_dict(state_dict, strict=True)

    def compute_model_digest(self) -> str:
        """Compute deterministic SHA-256 digest of neural network weights."""
        hasher = hashlib.sha256()
        for name, param in sorted(self.state_dict().items()):
            hasher.update(name.encode("utf-8"))
            hasher.update(param.cpu().numpy().tobytes())
        return hasher.hexdigest()


def get_parameters(net: nn.Module) -> List[np.ndarray]:
    """Extract ordered parameter tensors as NumPy ndarrays for Flower transmission."""
    return [val.cpu().numpy() for _, val in net.state_dict().items()]


def set_parameters(net: nn.Module, parameters: List[np.ndarray]) -> None:
    """Restore parameter tensors from Flower ndarrays into PyTorch state_dict."""
    params_dict = zip(net.state_dict().keys(), parameters, strict=True)
    state_dict = {k: torch.tensor(v) for k, v in params_dict}
    net.load_state_dict(state_dict, strict=True)


def compute_model_digest(net: nn.Module) -> str:
    """Compute deterministic SHA-256 digest of neural network weights."""
    hasher = hashlib.sha256()
    for name, param in sorted(net.state_dict().items()):
        hasher.update(name.encode("utf-8"))
        hasher.update(param.cpu().numpy().tobytes())
    return hasher.hexdigest()
