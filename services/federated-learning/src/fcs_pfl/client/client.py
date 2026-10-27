"""FCS-PFL Client: Flower NumPyClient implementation for ISP participants.

Integrates TabularMLPNet with local PyTorch training, Opacus DP-SGD,
and persistent PrivacyAccountant budget enforcement.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import flwr as fl
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from fcs_pfl.admission.validator import ParticipantAdmissionValidator
from fcs_pfl.client.loader import TenantPartitionLoader
from fcs_pfl.contracts.manifests import PrivacyReceipt, RoundManifest
from fcs_pfl.models.mlp import TabularMLPNet
from fcs_pfl.privacy.accountant import PrivacyAccountant
from fcs_pfl.privacy.engine import DPPrivacyEngine

logger = logging.getLogger(__name__)


class FCSFlowerClient(fl.client.NumPyClient):
    """Flower client representing an ISP participant in FCS-PFL."""

    def __init__(
        self,
        participant_id: str,
        partition_name: str = "iid",
        model: Optional[TabularMLPNet] = None,
        accountant: Optional[PrivacyAccountant] = None,
        dp_engine: Optional[DPPrivacyEngine] = None,
        batch_size: int = 64,
        local_epochs: int = 1,
        learning_rate: float = 0.001,
        weight_decay: float = 1e-4,
        use_dp: bool = False,
        validator: Optional[ParticipantAdmissionValidator] = None,
        manifest: Optional[RoundManifest] = None,
    ) -> None:
        super().__init__()
        self.participant_id = participant_id
        self.partition_name = partition_name
        self.batch_size = batch_size
        self.local_epochs = local_epochs
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.use_dp = use_dp

        # Shared MLP: use GroupNorm when DP is active, BatchNorm when research baseline
        self.model = model or TabularMLPNet(
            input_dim=14,
            hidden_dims=[64, 32],
            num_classes=2,
            use_group_norm=use_dp,
        )

        self.accountant = accountant
        self.dp_engine = dp_engine
        self.validator = validator or ParticipantAdmissionValidator()
        self.manifest = manifest

        # Data loader for client's specific tenant partition
        self.data_loader = TenantPartitionLoader(
            participant_id=self.participant_id,
            partition_name=self.partition_name,
        )
        self._train_loader: Optional[DataLoader] = None
        self._val_loader: Optional[DataLoader] = None

    def _prepare_data(self) -> Tuple[DataLoader, DataLoader]:
        """Lazy load client partition data into PyTorch DataLoaders."""
        if self._train_loader is None or self._val_loader is None:
            train_x, train_y = self.data_loader.load_train_tensors()
            val_x, val_y = self.data_loader.load_val_tensors()

            train_dataset = TensorDataset(train_x, train_y)
            val_dataset = TensorDataset(val_x, val_y)

            # Drop last batch for Opacus compatibility if DP is enabled
            drop_last = self.use_dp and len(train_dataset) > self.batch_size
            self._train_loader = DataLoader(
                train_dataset,
                batch_size=self.batch_size,
                shuffle=True,
                drop_last=drop_last,
            )
            self._val_loader = DataLoader(
                val_dataset,
                batch_size=self.batch_size,
                shuffle=False,
            )
        return self._train_loader, self._val_loader

    def get_parameters(self, config: Dict[str, Any]) -> List[np.ndarray]:
        """Return the current local model parameters as numpy arrays."""
        return self.model.get_parameters()

    def fit(
        self,
        parameters: List[np.ndarray],
        config: Dict[str, Any],
    ) -> Tuple[List[np.ndarray], int, Dict[str, Any]]:
        """Execute local training for one federated round.

        Enforces participant admission checks and cumulative privacy budget constraints.
        """
        round_id = str(config.get("round_id", "round_1"))
        job_id = str(config.get("job_id", "pfl_job_default"))

        # 1. Admission Check
        if self.manifest:
            is_valid, reason = self.validator.validate(self.manifest, self.participant_id)
            if not is_valid:
                logger.error("Admission check failed for %s: %s", self.participant_id, reason)
                raise PermissionError(f"Client admission rejected: {reason}")

        # 2. Cumulative Privacy Accounting Check (if DP is enabled)
        reservation_id: Optional[str] = None
        current_epsilon = 0.0
        current_delta = 0.0

        if self.use_dp and self.accountant:
            can_train, remaining = self.accountant.can_train(self.participant_id, estimated_epsilon=0.5)
            if not can_train:
                logger.error("Privacy budget exhausted for %s. Remaining eps: %.4f", self.participant_id, remaining)
                raise PermissionError(f"Privacy budget exhausted for {self.participant_id}: remaining eps {remaining:.4f}")

            # Reserve budget before local training begins
            reservation_id = self.accountant.reserve_budget(
                participant_id=self.participant_id,
                round_id=round_id,
                job_id=job_id,
                reserved_epsilon=0.5,
                reserved_delta=1e-5,
            )

        # 3. Update local model with incoming global parameters
        self.model.set_parameters(parameters)

        # 4. Prepare data
        train_loader, _ = self._prepare_data()
        num_examples = len(train_loader.dataset)  # type: ignore

        # 5. Local Training Loop
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=self.learning_rate,
            weight_decay=self.weight_decay,
        )

        model = self.model
        loader = train_loader

        # Attach Opacus DP-SGD if configured
        if self.use_dp and self.dp_engine:
            model, optimizer, loader = self.dp_engine.make_private(
                module=model,
                optimizer=optimizer,
                data_loader=train_loader,
            )

        model.train()
        total_loss = 0.0
        correct = 0
        total_samples = 0

        for _ in range(self.local_epochs):
            for batch_x, batch_y in loader:
                optimizer.zero_grad()
                logits = model(batch_x)
                loss = criterion(logits, batch_y)
                loss.backward()
                optimizer.step()

                total_loss += loss.item() * len(batch_y)
                preds = torch.argmax(logits, dim=-1)
                correct += (preds == batch_y).sum().item()
                total_samples += len(batch_y)

        avg_loss = total_loss / max(total_samples, 1)
        accuracy = correct / max(total_samples, 1)

        # 6. Commit privacy expenditure and get receipt
        if self.use_dp and self.accountant and self.dp_engine and reservation_id:
            current_epsilon, current_delta = self.dp_engine.get_epsilon_and_delta()
            # If current_epsilon is very small or zero on early steps, record minimum step loss
            step_eps = max(current_epsilon, 0.1)
            receipt: PrivacyReceipt = self.accountant.commit_spend(
                reservation_id=reservation_id,
                spent_epsilon=step_eps,
                spent_delta=current_delta if current_delta > 0 else 1e-5,
                model_digest=self.model.compute_model_digest(),
            )
            logger.info(
                "[%s] Round %s DP spend committed: spent_eps=%.4f (cum_eps=%.4f), receipt=%s",
                self.participant_id,
                round_id,
                step_eps,
                receipt.cumulative_epsilon,
                receipt.receipt_id,
            )

        metrics: Dict[str, Any] = {
            "participant_id": self.participant_id,
            "train_loss": float(avg_loss),
            "train_accuracy": float(accuracy),
            "num_samples": int(num_examples),
            "dp_enabled": bool(self.use_dp),
            "epsilon": float(current_epsilon),
            "delta": float(current_delta),
        }

        # Return updated local parameters
        updated_params = self.model.get_parameters()
        return updated_params, num_examples, metrics

    def evaluate(
        self,
        parameters: List[np.ndarray],
        config: Dict[str, Any],
    ) -> Tuple[float, int, Dict[str, Any]]:
        """Evaluate incoming parameters on local validation set."""
        self.model.set_parameters(parameters)
        _, val_loader = self._prepare_data()

        criterion = nn.CrossEntropyLoss()
        self.model.eval()

        total_loss = 0.0
        correct = 0
        total_samples = 0
        all_preds = []
        all_targets = []

        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                logits = self.model(batch_x)
                loss = criterion(logits, batch_y)
                total_loss += loss.item() * len(batch_y)

                preds = torch.argmax(logits, dim=-1)
                correct += (preds == batch_y).sum().item()
                total_samples += len(batch_y)

                all_preds.extend(preds.cpu().numpy().tolist())
                all_targets.extend(batch_y.cpu().numpy().tolist())

        avg_loss = total_loss / max(total_samples, 1)
        accuracy = correct / max(total_samples, 1)

        # Binary precision / recall / f1
        preds_arr = np.array(all_preds)
        targets_arr = np.array(all_targets)
        tp = np.sum((preds_arr == 1) & (targets_arr == 1))
        fp = np.sum((preds_arr == 1) & (targets_arr == 0))
        fn = np.sum((preds_arr == 0) & (targets_arr == 1))

        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        metrics: Dict[str, Any] = {
            "participant_id": self.participant_id,
            "val_loss": float(avg_loss),
            "val_accuracy": float(accuracy),
            "val_precision": float(precision),
            "val_recall": float(recall),
            "val_f1": float(f1),
        }

        return float(avg_loss), total_samples, metrics
