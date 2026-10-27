"""FCS-PFL Strategy: Customized FedAvg strategy for FCS federated learning.

Supports both equal-ISP weighting and sample-count weighting, metric
aggregation, and aggregate parameter validation.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import flwr as fl
import numpy as np
from flwr.common import (
    EvaluateIns,
    EvaluateRes,
    FitIns,
    FitRes,
    Metrics,
    MetricsAggregationFn,
    NDArrays,
    Parameters,
    Scalar,
    ndarrays_to_parameters,
    parameters_to_ndarrays,
)
from flwr.server.client_proxy import ClientProxy

logger = logging.getLogger(__name__)


def aggregate_metrics(metrics: List[Tuple[int, Metrics]]) -> Metrics:
    """Aggregate per-client evaluation/training metrics."""
    if not metrics:
        return {}

    total_examples = sum(num_examples for num_examples, _ in metrics)
    aggregated: Dict[str, Scalar] = {}

    keys = set()
    for _, m in metrics:
        keys.update(m.keys())

    for key in keys:
        values = []
        weights = []
        for num_examples, m in metrics:
            if key in m and isinstance(m[key], (int, float)):
                values.append(m[key])
                weights.append(num_examples)

        if values:
            if key in ("epsilon", "cum_epsilon", "delta"):
                # For privacy budget, track the maximum spend among participants
                aggregated[f"max_{key}"] = float(np.max(values))
            else:
                # Weighted average for utility metrics
                weighted_avg = sum(v * w for v, w in zip(values, weights)) / max(sum(weights), 1)
                aggregated[key] = float(weighted_avg)

    return aggregated


class FCSFedAvgStrategy(fl.server.strategy.FedAvg):
    """Federated Averaging strategy tailored for FCS-PFL with ISP fairness and safety."""

    def __init__(
        self,
        fraction_fit: float = 1.0,
        fraction_evaluate: float = 1.0,
        min_fit_clients: int = 5,
        min_evaluate_clients: int = 5,
        min_available_clients: int = 7,
        equal_isp_weighting: bool = True,
        initial_parameters: Optional[Parameters] = None,
        fit_metrics_aggregation_fn: Optional[MetricsAggregationFn] = None,
        evaluate_metrics_aggregation_fn: Optional[MetricsAggregationFn] = None,
    ) -> None:
        super().__init__(
            fraction_fit=fraction_fit,
            fraction_evaluate=fraction_evaluate,
            min_fit_clients=min_fit_clients,
            min_evaluate_clients=min_evaluate_clients,
            min_available_clients=min_available_clients,
            initial_parameters=initial_parameters,
            fit_metrics_aggregation_fn=fit_metrics_aggregation_fn or aggregate_metrics,
            evaluate_metrics_aggregation_fn=evaluate_metrics_aggregation_fn or aggregate_metrics,
        )
        self.equal_isp_weighting = equal_isp_weighting
        self.round_history: List[Dict[str, Any]] = []

    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, FitRes]],
        failures: List[Union[Tuple[ClientProxy, FitRes], BaseException]],
    ) -> Tuple[Optional[Parameters], Dict[str, Scalar]]:
        """Aggregate fit results using either equal ISP weighting or sample-count weighting."""
        if not results:
            logger.warning("[Round %d] No client fit results to aggregate", server_round)
            return None, {}

        # Check for failures
        if failures:
            logger.warning("[Round %d] %d client failures encountered", server_round, len(failures))

        # Check threshold
        if len(results) < self.min_fit_clients:
            logger.error(
                "[Round %d] Received %d results, below minimum threshold %d. Aborting aggregate.",
                server_round,
                len(results),
                self.min_fit_clients,
            )
            return None, {"error": "insufficient_cohort"}

        if self.equal_isp_weighting:
            # Equal weighting: each participating ISP contributes exactly 1 / N to the aggregate
            weights_results: List[Tuple[NDArrays, int]] = []
            for _, fit_res in results:
                ndarrays = parameters_to_ndarrays(fit_res.parameters)
                weights_results.append((ndarrays, 1))

            aggregated_ndarrays = self._aggregate_equal(weights_results)
        else:
            # Sample-weighted aggregation
            weights_results = [
                (parameters_to_ndarrays(fit_res.parameters), fit_res.num_examples)
                for _, fit_res in results
            ]
            aggregated_ndarrays = fl.server.strategy.aggregate.aggregate(weights_results)

        # Validate aggregated parameters for NaN / Inf
        for arr in aggregated_ndarrays:
            if not np.all(np.isfinite(arr)):
                logger.error("[Round %d] Aggregated weights contain NaN or Inf! Aborting.", server_round)
                return None, {"error": "numeric_instability_nan_inf"}

        parameters_aggregated = ndarrays_to_parameters(aggregated_ndarrays)

        # Aggregate metrics
        metrics_aggregated: Dict[str, Scalar] = {}
        if self.fit_metrics_aggregation_fn:
            fit_metrics = [(res.num_examples, res.metrics) for _, res in results]
            metrics_aggregated = self.fit_metrics_aggregation_fn(fit_metrics)

        metrics_aggregated["participating_clients"] = len(results)
        metrics_aggregated["failed_clients"] = len(failures)
        metrics_aggregated["equal_weighting"] = 1 if self.equal_isp_weighting else 0

        self.round_history.append({
            "round": server_round,
            "metrics": metrics_aggregated,
            "num_participants": len(results),
        })

        return parameters_aggregated, metrics_aggregated

    def _aggregate_equal(self, results: List[Tuple[NDArrays, int]]) -> NDArrays:
        """Compute the unweighted (equal) arithmetic average of client weight tensors."""
        num_clients = len(results)
        # Initialize accumulated tensors with zeros
        accumulated = [np.zeros_like(arr, dtype=np.float64) for arr in results[0][0]]

        for client_weights, _ in results:
            for i, layer in enumerate(client_weights):
                accumulated[i] += layer.astype(np.float64)

        # Average
        averaged = [layer / float(num_clients) for layer in accumulated]
        return [layer.astype(results[0][0][i].dtype) for i, layer in enumerate(averaged)]
