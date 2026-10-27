"""Flower ServerApp factory for FCS-PFL."""

from __future__ import annotations

import logging
from typing import Optional

from flwr.app.message.context import Context
from flwr.compat.server.serverapp_components import ServerAppComponents
from flwr.server import ServerApp, ServerConfig
from flwr.server.workflow import SecAggPlusWorkflow

from fcs_pfl.server.strategy import FCSFedAvgStrategy

logger = logging.getLogger(__name__)


def create_server_app(
    strategy: Optional[FCSFedAvgStrategy] = None,
    num_rounds: int = 3,
    use_secagg: bool = False,
    num_shares: int = 7,
    reconstruction_threshold: int = 5,
    clipping_range: float = 8.0,
    quantization_range: int = 4194304,
) -> ServerApp:
    """Create a configured Flower ServerApp.

    If use_secagg is True:
        Uses SecAggPlusWorkflow with the specified reconstruction threshold (k=5/7)
        and clipping/quantization parameters.
    Else:
        Uses standard FedAvg strategy workflow.
    """
    strat = strategy or FCSFedAvgStrategy(
        min_fit_clients=reconstruction_threshold,
        min_evaluate_clients=reconstruction_threshold,
        min_available_clients=num_shares,
        equal_isp_weighting=True,
    )

    if use_secagg:
        app = ServerApp()
        workflow = SecAggPlusWorkflow(
            num_shares=num_shares,
            reconstruction_threshold=reconstruction_threshold,
            clipping_range=clipping_range,
            quantization_range=quantization_range,
        )

        @app.main()
        def main(grid, context: Context):  # type: ignore
            logger.info(
                "Executing SecAggPlusWorkflow: num_shares=%d, threshold=%d",
                num_shares,
                reconstruction_threshold,
            )
            workflow(grid, context)

        return app

    # Standard FedAvg workflow
    def server_fn(context: Context) -> ServerAppComponents:
        return ServerAppComponents(
            strategy=strat,
            config=ServerConfig(num_rounds=num_rounds),
        )

    return ServerApp(server_fn=server_fn)
