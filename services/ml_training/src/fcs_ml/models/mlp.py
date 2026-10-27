"""PyTorch Multi-Layer Perceptron (MLP) for tabular intrusion detection."""

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

from .base import BaseFCSModel


class TabularMLPNet(nn.Module):
    """
    Standard reconstructible PyTorch neural network for tabular NetFlow features.
    Designed for local CPU training and forward-compatible with Flower federated learning.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dims: list[int] | None = None,
        output_dim: int = 1,
        dropout_rate: float = 0.2,
        use_batch_norm: bool = True,
    ) -> None:
        super().__init__()
        hidden_dims = hidden_dims or [128, 64]
        layers: list[nn.Module] = []

        prev_dim = input_dim
        for h_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, h_dim))
            if use_batch_norm:
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
        self.dropout_rate = dropout_rate
        self.use_batch_norm = use_batch_norm

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)

    def get_parameter_count(self) -> int:
        """Total trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


class PyTorchMLPModel(BaseFCSModel):
    """CPU-efficient PyTorch tabular classifier with AdamW and validation early stopping."""

    def __init__(
        self,
        hidden_dims: list[int] | None = None,
        dropout_rate: float = 0.2,
        learning_rate: float = 0.001,
        weight_decay: float = 0.0001,
        batch_size: int = 64,
        epochs: int = 25,
        early_stopping_patience: int = 5,
        use_batch_norm: bool = True,
        is_multiclass: bool = False,
        num_classes: int = 2,
        random_seed: int = 42,
    ) -> None:
        super().__init__("PyTorchMLP", random_seed)
        self.hidden_dims = hidden_dims or [128, 64]
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.batch_size = batch_size
        self.epochs = epochs
        self.early_stopping_patience = early_stopping_patience
        self.use_batch_norm = use_batch_norm
        self.is_multiclass = is_multiclass
        self.num_classes = num_classes

        torch.manual_seed(self.random_seed)
        np.random.seed(self.random_seed)

        self._scaler = StandardScaler()
        self.net: TabularMLPNet | None = None
        self.training_history: list[dict[str, float]] = []

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        feature_names: list[str] | None = None,
    ) -> "PyTorchMLPModel":
        self.feature_names = feature_names or [f"f_{i}" for i in range(X_train.shape[1])]
        input_dim = X_train.shape[1]
        output_dim = self.num_classes if self.is_multiclass else 1

        # Fit standard scaler strictly on training split
        X_train_s = self._scaler.fit_transform(X_train)

        self.net = TabularMLPNet(
            input_dim=input_dim,
            hidden_dims=self.hidden_dims,
            output_dim=output_dim,
            dropout_rate=self.dropout_rate,
            use_batch_norm=self.use_batch_norm,
        )

        train_tensor_x = torch.tensor(X_train_s, dtype=torch.float32)
        if self.is_multiclass:
            train_tensor_y = torch.tensor(y_train, dtype=torch.long)
            criterion: nn.Module = nn.CrossEntropyLoss()
        else:
            train_tensor_y = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1)
            criterion = nn.BCEWithLogitsLoss()

        train_loader = DataLoader(
            TensorDataset(train_tensor_x, train_tensor_y),
            batch_size=self.batch_size,
            shuffle=True,
            drop_last=False,
        )

        has_val = X_val is not None and y_val is not None and len(X_val) > 0
        if has_val:
            assert X_val is not None and y_val is not None
            X_val_s = self._scaler.transform(X_val)
            val_tensor_x = torch.tensor(X_val_s, dtype=torch.float32)
            if self.is_multiclass:
                val_tensor_y = torch.tensor(y_val, dtype=torch.long)
            else:
                val_tensor_y = torch.tensor(y_val, dtype=torch.float32).unsqueeze(1)

        optimizer = torch.optim.AdamW(
            self.net.parameters(),
            lr=self.learning_rate,
            weight_decay=self.weight_decay,
        )

        best_val_loss = float("inf")
        best_state: dict[str, Any] | None = None
        patience_counter = 0

        self.net.train()
        for epoch in range(self.epochs):
            self.net.train()
            running_train_loss = 0.0
            for batch_x, batch_y in train_loader:
                optimizer.zero_grad()
                preds = self.net(batch_x)
                loss = criterion(preds, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.net.parameters(), max_norm=1.0)
                optimizer.step()
                running_train_loss += loss.item() * len(batch_x)

            epoch_train_loss = running_train_loss / len(train_tensor_x)

            epoch_val_loss = epoch_train_loss
            if has_val:
                self.net.eval()
                with torch.no_grad():
                    val_preds = self.net(val_tensor_x)
                    val_loss_t = criterion(val_preds, val_tensor_y)
                    epoch_val_loss = val_loss_t.item()

                if epoch_val_loss < best_val_loss - 1e-4:
                    best_val_loss = epoch_val_loss
                    best_state = {k: v.cpu().clone() for k, v in self.net.state_dict().items()}
                    patience_counter = 0
                else:
                    patience_counter += 1
                    if patience_counter >= self.early_stopping_patience:
                        break

            self.training_history.append({
                "epoch": float(epoch + 1),
                "train_loss": float(epoch_train_loss),
                "val_loss": float(epoch_val_loss),
            })

        if best_state is not None:
            self.net.load_state_dict(best_state)

        self.net.eval()
        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted or self.net is None:
            raise RuntimeError("Model is not fitted yet.")
        self.net.eval()
        X_s = self._scaler.transform(X)
        tensor_x = torch.tensor(X_s, dtype=torch.float32)

        with torch.no_grad():
            logits = self.net(tensor_x)
            if self.is_multiclass:
                probs = torch.softmax(logits, dim=1).cpu().numpy()
                return probs
            else:
                prob_1 = torch.sigmoid(logits).cpu().numpy()
                prob_0 = 1.0 - prob_1
                return np.hstack([prob_0, prob_1])

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        proba = self.predict_proba(X)
        if self.is_multiclass:
            return np.argmax(proba, axis=1)
        return (proba[:, 1] >= threshold).astype(np.int64)

    def get_params(self) -> dict[str, Any]:
        param_count = self.net.get_parameter_count() if self.net is not None else 0
        return {
            "model_family": "PyTorchMLP",
            "hidden_dims": self.hidden_dims,
            "dropout_rate": self.dropout_rate,
            "learning_rate": self.learning_rate,
            "weight_decay": self.weight_decay,
            "batch_size": self.batch_size,
            "epochs": self.epochs,
            "use_batch_norm": self.use_batch_norm,
            "is_multiclass": self.is_multiclass,
            "num_classes": self.num_classes,
            "random_seed": self.random_seed,
            "parameter_count": param_count,
        }

    def save(self, filepath: Path | str) -> str:
        """Save PyTorch state_dict and sidecar metadata JSON."""
        if not self.is_fitted or self.net is None:
            raise RuntimeError("Cannot save unfitted PyTorch model.")
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)

        pt_path = p.with_suffix(".pt")
        meta_path = p.with_suffix(".json")

        torch.save(self.net.state_dict(), str(pt_path))

        meta = {
            "model_family": "PyTorchMLP",
            "input_dim": len(self.feature_names),
            "hidden_dims": self.hidden_dims,
            "output_dim": self.num_classes if self.is_multiclass else 1,
            "dropout_rate": self.dropout_rate,
            "use_batch_norm": self.use_batch_norm,
            "is_multiclass": self.is_multiclass,
            "num_classes": self.num_classes,
            "random_seed": self.random_seed,
            "feature_names": self.feature_names,
            "scaler_mean": self._scaler.mean_.tolist() if self._scaler.mean_ is not None else [],
            "scaler_scale": self._scaler.scale_.tolist() if self._scaler.scale_ is not None else [],
            "parameter_count": self.net.get_parameter_count(),
            "is_fitted": self.is_fitted,
        }
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        combined_bytes = pt_path.read_bytes() + meta_path.read_bytes()
        return hashlib.sha256(combined_bytes).hexdigest()

    @classmethod
    def load(cls, filepath: Path | str) -> "PyTorchMLPModel":
        p = Path(filepath)
        pt_path = p.with_suffix(".pt")
        meta_path = p.with_suffix(".json")

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        model = cls(
            hidden_dims=meta["hidden_dims"],
            dropout_rate=meta["dropout_rate"],
            use_batch_norm=meta["use_batch_norm"],
            is_multiclass=meta["is_multiclass"],
            num_classes=meta["num_classes"],
            random_seed=meta["random_seed"],
        )
        model.feature_names = meta.get("feature_names", [])

        # Restore scaler
        model._scaler.mean_ = np.array(meta["scaler_mean"], dtype=np.float64)
        model._scaler.scale_ = np.array(meta["scaler_scale"], dtype=np.float64)
        model._scaler.var_ = model._scaler.scale_ ** 2
        model._scaler.n_features_in_ = len(model.feature_names)

        # Construct network
        model.net = TabularMLPNet(
            input_dim=meta["input_dim"],
            hidden_dims=meta["hidden_dims"],
            output_dim=meta["output_dim"],
            dropout_rate=meta["dropout_rate"],
            use_batch_norm=meta["use_batch_norm"],
        )
        state_dict = torch.load(str(pt_path), map_location="cpu", weights_only=True)
        model.net.load_state_dict(state_dict)
        model.net.eval()
        model.is_fitted = meta.get("is_fitted", True)
        return model
