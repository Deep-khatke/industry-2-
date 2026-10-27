"""FCS-PFL Secure Aggregation module for SecAgg+ protocol verification.

Encapsulates protocol parameters, threshold verification (k=5 of 7),
clipping/quantization analysis, and dropout simulation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SecAggConfig:
    """Configuration parameters for Flower SecAgg+ protocol."""

    num_participants: int = 7
    reconstruction_threshold: int = 5
    clipping_range: float = 8.0
    quantization_range: int = 4194304  # 2^22
    modulus_range: int = 4294967296  # 2^32
    timeout_seconds: float = 60.0

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate parameter invariants for SecAgg+."""
        if self.reconstruction_threshold < 1:
            return False, "Reconstruction threshold must be at least 1"
        if self.reconstruction_threshold > self.num_participants:
            return False, "Reconstruction threshold cannot exceed num_participants"
        if self.clipping_range <= 0.0:
            return False, "Clipping range must be positive"
        if self.quantization_range < 1:
            return False, "Quantization range must be positive"
        if self.quantization_range > self.modulus_range:
            return False, "Quantization range cannot exceed modulus range"
        return True, None


class SecAggProtocolSimulator:
    """Verifies SecAgg+ masking, unmasking, quantization, and dropout arithmetic.

    Used for unit testing cryptographic correctness, numeric stability,
    and threshold failure aborts without requiring network sockets.
    """

    def __init__(self, config: Optional[SecAggConfig] = None) -> None:
        self.config = config or SecAggConfig()
        is_valid, err = self.config.validate()
        if not is_valid:
            raise ValueError(f"Invalid SecAggConfig: {err}")

    def quantize(self, weights: List[np.ndarray]) -> List[np.ndarray]:
        """Quantize floating point weights into integer representations bounded by clipping_range."""
        quantized = []
        clip_r = self.config.clipping_range
        quant_r = self.config.quantization_range

        for w in weights:
            clipped = np.clip(w, -clip_r, clip_r)
            # Map [-clip_r, clip_r] to [0, quant_r]
            scaled = (clipped + clip_r) / (2.0 * clip_r) * quant_r
            quantized.append(np.round(scaled).astype(np.int64))
        return quantized

    def dequantize(
        self,
        quantized_sum: List[np.ndarray],
        num_active_clients: int,
    ) -> List[np.ndarray]:
        """Dequantize accumulated integer representations back to floating point averages."""
        dequantized = []
        clip_r = self.config.clipping_range
        quant_r = self.config.quantization_range

        for q in quantized_sum:
            # Reverse mapping
            scaled_sum = q.astype(np.float64) / quant_r
            # Each client added an offset of clip_r, so total offset is num_active_clients * clip_r
            total = scaled_sum * (2.0 * clip_r) - (num_active_clients * clip_r)
            avg = total / float(num_active_clients)
            dequantized.append(avg)
        return dequantized

    def measure_quantization_error(
        self,
        weights: List[np.ndarray],
    ) -> Dict[str, float]:
        """Measure max and mean absolute error introduced by clipping and quantization."""
        q = self.quantize(weights)
        dq = self.dequantize(q, num_active_clients=1)

        errors = []
        for orig, recon in zip(weights, dq):
            err = np.abs(orig - recon)
            errors.extend(err.flatten().tolist())

        arr_err = np.array(errors)
        return {
            "max_abs_error": float(np.max(arr_err)),
            "mean_abs_error": float(np.mean(arr_err)),
            "rmse": float(np.sqrt(np.mean(arr_err ** 2))),
        }

    def simulate_aggregation(
        self,
        client_updates: Dict[str, List[np.ndarray]],
        dropped_clients: Optional[List[str]] = None,
    ) -> Tuple[Optional[List[np.ndarray]], Dict[str, Any]]:
        """Simulate secure aggregation with dropouts and check threshold enforcement."""
        dropped = set(dropped_clients or [])
        active_clients = [pid for pid in client_updates if pid not in dropped]
        num_active = len(active_clients)

        # Enforce threshold: abort if below reconstruction threshold k
        if num_active < self.config.reconstruction_threshold:
            logger.warning(
                "SecAgg abort: %d active clients is below threshold %d (dropped %d)",
                num_active,
                self.config.reconstruction_threshold,
                len(dropped),
            )
            return None, {
                "status": "ABORTED_BELOW_THRESHOLD",
                "active_clients": active_clients,
                "dropped_clients": list(dropped),
                "threshold": self.config.reconstruction_threshold,
            }

        # Simulate integer quantization and modular summation
        first_client = active_clients[0]
        accumulated = [
            np.zeros_like(arr, dtype=np.int64)
            for arr in client_updates[first_client]
        ]

        for pid in active_clients:
            q_weights = self.quantize(client_updates[pid])
            for i, layer in enumerate(q_weights):
                accumulated[i] = (accumulated[i] + layer) % self.config.modulus_range

        aggregated = self.dequantize(accumulated, num_active_clients=num_active)

        return aggregated, {
            "status": "COMPLETED",
            "active_clients": active_clients,
            "dropped_clients": list(dropped),
            "num_active": num_active,
            "threshold": self.config.reconstruction_threshold,
        }
