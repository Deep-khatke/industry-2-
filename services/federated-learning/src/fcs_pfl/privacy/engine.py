"""Opacus Differential Privacy Engine integration for client-local DP-SGD."""

from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

import torch
import torch.nn as nn
from opacus import PrivacyEngine
from opacus.validators import ModuleValidator
from torch.utils.data import DataLoader

logger = logging.getLogger(__name__)


class DPPrivacyEngine:
    """
    Integrates Opacus DP-SGD into client-local model training.
    Enforces per-example gradient clipping and calibrated Gaussian noise addition.
    """

    def __init__(
        self,
        max_grad_norm: float = 1.0,
        noise_multiplier: float = 1.1,
        target_delta: float = 1e-5,
        target_epsilon: float = 2.0,
    ) -> None:
        self.max_grad_norm = max_grad_norm
        self.noise_multiplier = noise_multiplier
        self.target_delta = target_delta
        self.target_epsilon = target_epsilon
        self.privacy_engine: Optional[PrivacyEngine] = None

    def prepare_private_training(
        self,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        data_loader: DataLoader,
    ) -> Tuple[nn.Module, torch.optim.Optimizer, DataLoader]:
        """
        Validates model layers for DP compatibility and attaches Opacus PrivacyEngine.
        Replaces BatchNorm with GroupNorm if necessary using ModuleValidator.
        """
        if not ModuleValidator.is_valid(model):
            logger.info("Model contains layers incompatible with Opacus (e.g. BatchNorm). Applying ModuleValidator.fix().")
            model = ModuleValidator.fix(model)

        self.privacy_engine = PrivacyEngine()
        model, optimizer, data_loader = self.privacy_engine.make_private(
            module=model,
            optimizer=optimizer,
            data_loader=data_loader,
            noise_multiplier=self.noise_multiplier,
            max_grad_norm=self.max_grad_norm,
        )
        return model, optimizer, data_loader

    def make_private(
        self,
        module: nn.Module,
        optimizer: torch.optim.Optimizer,
        data_loader: DataLoader,
    ) -> Tuple[nn.Module, torch.optim.Optimizer, DataLoader]:
        """Alias for prepare_private_training."""
        return self.prepare_private_training(model=module, optimizer=optimizer, data_loader=data_loader)

    def get_privacy_spent(self) -> Tuple[float, float]:
        """Query cumulative epsilon for target delta from Opacus accountant."""
        if not self.privacy_engine:
            return 0.0, self.target_delta
        try:
            eps = float(self.privacy_engine.get_epsilon(delta=self.target_delta))
            return eps, self.target_delta
        except Exception as e:
            logger.warning("Error computing privacy loss: %s", e)
            return 0.0, self.target_delta

    def get_epsilon_and_delta(self) -> Tuple[float, float]:
        """Alias for get_privacy_spent."""
        return self.get_privacy_spent()
