"""Flower ClientApp factory and lifecycle handler for FCS-PFL."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from flwr.app.message.context import Context
from flwr.client import Client, ClientApp
from flwr.client.mod import secaggplus_mod

from fcs_pfl.admission.validator import ParticipantAdmissionValidator
from fcs_pfl.client.client import FCSFlowerClient
from fcs_pfl.contracts.manifests import RoundManifest
from fcs_pfl.privacy.accountant import PrivacyAccountant
from fcs_pfl.privacy.engine import DPPrivacyEngine

logger = logging.getLogger(__name__)

PARTICIPANTS = [f"isp_{i:02d}" for i in range(1, 8)]


def make_client_fn(
    partition_name: str = "iid",
    use_dp: bool = False,
    epsilon_target: float = 2.0,
    delta_target: float = 1e-5,
    max_grad_norm: float = 1.0,
    noise_multiplier: float = 1.0,
    batch_size: int = 64,
    local_epochs: int = 1,
    learning_rate: float = 0.001,
    accountant: Optional[PrivacyAccountant] = None,
    manifest: Optional[RoundManifest] = None,
) -> Callable[[Context], Client]:
    """Generate a client_fn callback for Flower ClientApp."""

    def client_fn(context: Context) -> Client:
        # Determine participant ID from node_config, run_config, or node_id
        partition_id = None
        if context.node_config:
            partition_id = context.node_config.get("partition-id")

        if partition_id is not None:
            idx = int(partition_id) % len(PARTICIPANTS)
        elif context.node_id is not None:
            idx = int(context.node_id) % len(PARTICIPANTS)
        else:
            idx = 0

        participant_id = PARTICIPANTS[idx]

        # Initialize DP engine if requested
        dp_engine = None
        if use_dp:
            dp_engine = DPPrivacyEngine(
                target_epsilon=epsilon_target,
                target_delta=delta_target,
                max_grad_norm=max_grad_norm,
                noise_multiplier=noise_multiplier,
            )

        client = FCSFlowerClient(
            participant_id=participant_id,
            partition_name=partition_name,
            accountant=accountant,
            dp_engine=dp_engine,
            batch_size=batch_size,
            local_epochs=local_epochs,
            learning_rate=learning_rate,
            use_dp=use_dp,
            manifest=manifest,
        )
        return client.to_client()

    return client_fn


def create_client_app(
    partition_name: str = "iid",
    use_secagg: bool = False,
    use_dp: bool = False,
    epsilon_target: float = 2.0,
    delta_target: float = 1e-5,
    max_grad_norm: float = 1.0,
    noise_multiplier: float = 1.0,
    batch_size: int = 64,
    local_epochs: int = 1,
    learning_rate: float = 0.001,
    accountant: Optional[PrivacyAccountant] = None,
    manifest: Optional[RoundManifest] = None,
) -> ClientApp:
    """Build a configured Flower ClientApp.

    If use_secagg is True, attaches secaggplus_mod to client execution pipeline.
    """
    client_fn = make_client_fn(
        partition_name=partition_name,
        use_dp=use_dp,
        epsilon_target=epsilon_target,
        delta_target=delta_target,
        max_grad_norm=max_grad_norm,
        noise_multiplier=noise_multiplier,
        batch_size=batch_size,
        local_epochs=local_epochs,
        learning_rate=learning_rate,
        accountant=accountant,
        manifest=manifest,
    )

    mods = []
    if use_secagg:
        mods.append(secaggplus_mod)

    return ClientApp(client_fn=client_fn, mods=mods if mods else None)
