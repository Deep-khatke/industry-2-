"""PyTorch lightweight MLP Autoencoder for unsupervised flow anomaly reconstruction."""

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


class _AutoencoderNet(nn.Module):
    """Feedforward reconstruction network."""

    def __init__(self, input_dim: int, hidden_dim: int = 16, latent_dim: int = 8) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, latent_dim),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        encoded = self.encoder(x)
        return self.decoder(encoded)


class AutoencoderAnomalyModel(BaseFCSModel):
    """
    Deep autoencoder anomaly detector evaluated where CPU/memory resources permit.
    Detects intrusions via elevated feature reconstruction error on normal ISP baseline distributions.
    """

    def __init__(
        self,
        hidden_dim: int = 16,
        latent_dim: int = 8,
        learning_rate: float = 0.005,
        epochs: int = 25,
        batch_size: int = 32,
        random_seed: int = 42,
        tenant_id: str = "global",
    ) -> None:
        super().__init__("Autoencoder", random_seed)
        self.hidden_dim = hidden_dim
        self.latent_dim = latent_dim
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self.tenant_id = tenant_id
        self._scaler = StandardScaler()
        self._net: _AutoencoderNet | None = None
        self.reconstruction_threshold_: float = 0.0
        self.sigmoid_scale_: float = 2.0

        torch.manual_seed(self.random_seed)

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray | None = None,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        feature_names: list[str] | None = None,
    ) -> "AutoencoderAnomalyModel":
        self.feature_names = feature_names or []
        if y_train is not None:
            benign_mask = y_train == 0
            X_fit = X_train[benign_mask] if np.sum(benign_mask) > 0 else X_train
        else:
            X_fit = X_train

        X_clean = np.nan_to_num(X_fit, nan=0.0, posinf=1e6, neginf=-1e6)
        X_scaled = self._scaler.fit_transform(X_clean)

        input_dim = X_scaled.shape[1]
        self._net = _AutoencoderNet(input_dim, self.hidden_dim, self.latent_dim)
        optimizer = torch.optim.Adam(self._net.parameters(), lr=self.learning_rate, weight_decay=1e-5)
        criterion = nn.MSELoss()

        tensor_x = torch.tensor(X_scaled, dtype=torch.float32)
        dataset = TensorDataset(tensor_x)
        loader = DataLoader(dataset, batch_size=min(self.batch_size, len(tensor_x)), shuffle=True)

        self._net.train()
        for _ in range(self.epochs):
            for (batch_x,) in loader:
                if len(batch_x) < 2:
                    continue
                optimizer.zero_grad()
                recon = self._net(batch_x)
                loss = criterion(recon, batch_x)
                loss.backward()
                optimizer.step()

        # Compute reconstruction threshold on training data (95th percentile)
        self._net.eval()
        with torch.no_grad():
            full_recon = self._net(tensor_x)
            mse = torch.mean((full_recon - tensor_x) ** 2, dim=1).numpy()
            self.reconstruction_threshold_ = float(np.percentile(mse, 95.0))
            std_mse = float(np.std(mse)) if np.std(mse) > 0 else 1.0
            self.sigmoid_scale_ = float(2.0 / std_mse)

        self.is_fitted = True
        return self

    def reconstruction_error(self, X: np.ndarray) -> np.ndarray:
        """Compute sample-wise Mean Squared Error reconstruction loss."""
        if not self.is_fitted or self._net is None:
            raise RuntimeError("Model is not fitted.")
        X_clean = np.nan_to_num(X, nan=0.0, posinf=1e6, neginf=-1e6)
        X_scaled = self._scaler.transform(X_clean)
        tensor_x = torch.tensor(X_scaled, dtype=torch.float32)

        self._net.eval()
        with torch.no_grad():
            recon = self._net(tensor_x)
            mse = torch.mean((recon - tensor_x) ** 2, dim=1).numpy()
        return mse

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Map MSE reconstruction error to calibrated anomaly probability.
        Returns shape (N, 2): [P(Normal), P(Anomaly)].
        """
        mse = self.reconstruction_error(X)
        diff = mse - self.reconstruction_threshold_
        z = self.sigmoid_scale_ * diff
        p_anomaly = 1.0 / (1.0 + np.exp(np.clip(-z, -50.0, 50.0)))
        p_anomaly = np.clip(p_anomaly, 0.0, 1.0)
        p_normal = 1.0 - p_anomaly
        return np.vstack([p_normal, p_anomaly]).T

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        proba = self.predict_proba(X)
        return (proba[:, 1] >= threshold).astype(np.int64)

    def get_params(self) -> dict[str, Any]:
        return {
            "model_family": "Autoencoder",
            "hidden_dim": self.hidden_dim,
            "latent_dim": self.latent_dim,
            "learning_rate": self.learning_rate,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "random_seed": self.random_seed,
            "tenant_id": self.tenant_id,
            "reconstruction_threshold": self.reconstruction_threshold_,
            "sigmoid_scale": self.sigmoid_scale_,
            "feature_names": self.feature_names,
            "is_fitted": self.is_fitted,
        }

    def save(self, filepath: Path | str) -> str:
        """Save PyTorch weights (.pt) and metadata JSON with deterministic SHA-256."""
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)

        pt_path = p.with_suffix(".pt")
        meta_path = p.with_suffix(".json")

        if self._net is not None:
            torch.save(self._net.state_dict(), pt_path)
        else:
            pt_path.write_bytes(b"")

        meta = {
            "model_family": "Autoencoder",
            "hidden_dim": self.hidden_dim,
            "latent_dim": self.latent_dim,
            "learning_rate": self.learning_rate,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "random_seed": self.random_seed,
            "tenant_id": self.tenant_id,
            "reconstruction_threshold": self.reconstruction_threshold_,
            "sigmoid_scale": self.sigmoid_scale_,
            "feature_names": self.feature_names,
            "scaler_mean": self._scaler.mean_.tolist() if hasattr(self._scaler, "mean_") and self._scaler.mean_ is not None else [],
            "scaler_scale": self._scaler.scale_.tolist() if hasattr(self._scaler, "scale_") and self._scaler.scale_ is not None else [],
            "is_fitted": self.is_fitted,
        }
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        combined = pt_path.read_bytes() + meta_path.read_bytes()
        return hashlib.sha256(combined).hexdigest()

    @classmethod
    def load(cls, filepath: Path | str) -> "AutoencoderAnomalyModel":
        p = Path(filepath)
        pt_path = p.with_suffix(".pt")
        meta_path = p.with_suffix(".json")

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        model = cls(
            hidden_dim=meta["hidden_dim"],
            latent_dim=meta["latent_dim"],
            learning_rate=meta["learning_rate"],
            epochs=meta["epochs"],
            batch_size=meta["batch_size"],
            random_seed=meta["random_seed"],
            tenant_id=meta.get("tenant_id", "global"),
        )
        model.feature_names = meta.get("feature_names", [])
        model.reconstruction_threshold_ = meta.get("reconstruction_threshold", 0.0)
        model.sigmoid_scale_ = meta.get("sigmoid_scale", 2.0)
        model.is_fitted = meta.get("is_fitted", True)

        input_dim = len(model.feature_names)
        model._net = _AutoencoderNet(input_dim, model.hidden_dim, model.latent_dim)
        if pt_path.exists() and pt_path.stat().st_size > 0:
            model._net.load_state_dict(torch.load(pt_path, weights_only=True))
        model._net.eval()

        if meta.get("scaler_mean"):
            model._scaler.mean_ = np.array(meta["scaler_mean"], dtype=np.float64)
            model._scaler.scale_ = np.array(meta["scaler_scale"], dtype=np.float64)
            model._scaler.var_ = model._scaler.scale_ ** 2
            model._scaler.n_features_in_ = len(model.feature_names)

        return model
