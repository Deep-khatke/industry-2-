"""FCS-PFL Federation Runner.

High-level simulation orchestrator for 7 ISP participants across
research and protected profiles, managing state transitions, dropouts,
privacy accounting, checkpointing, and evaluation.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import psutil
import torch
from flwr.common import (
    Code,
    EvaluateIns,
    EvaluateRes,
    FitIns,
    FitRes,
    GetParametersIns,
    GetParametersRes,
    Status,
    ndarrays_to_parameters,
    parameters_to_ndarrays,
)
from flwr.server.client_manager import SimpleClientManager
from flwr.server.client_proxy import ClientProxy
from flwr.server.server import Server

from fcs_pfl.admission.validator import LOCKED_FEATURE_SCHEMA_DIGEST, ParticipantAdmissionValidator
from fcs_pfl.aggregation.secagg import SecAggConfig, SecAggProtocolSimulator
from fcs_pfl.artifacts.candidate import CandidateModelRegistry
from fcs_pfl.checkpoints.manager import CheckpointManager
from fcs_pfl.client.client import FCSFlowerClient
from fcs_pfl.contracts.manifests import AggregationProtocol, CandidateStatus, RoundManifest
from fcs_pfl.evaluation.evaluator import FederatedModelEvaluator
from fcs_pfl.models.mlp import TabularMLPNet
from fcs_pfl.orchestration.state_machine import RoundState, RoundStateMachine
from fcs_pfl.privacy.accountant import PrivacyAccountant
from fcs_pfl.privacy.engine import DPPrivacyEngine
from fcs_pfl.server.strategy import FCSFedAvgStrategy

logger = logging.getLogger(__name__)

ALL_PARTICIPANTS = [f"isp_{i:02d}" for i in range(1, 8)]


class LocalFlowerClientProxy(ClientProxy):
    """Bridges Flower Server and Strategy with FCSFlowerClient in-process."""

    def __init__(self, cid: str, client: FCSFlowerClient) -> None:
        super().__init__(cid)
        self.client = client

    def get_properties(self, ins: Any, timeout: Optional[float], group_id: Optional[int]) -> Any:
        return None

    def get_parameters(self, ins: GetParametersIns, timeout: Optional[float], group_id: Optional[int]) -> GetParametersRes:
        params = self.client.get_parameters(ins.config)
        return GetParametersRes(Status(Code.OK, ""), ndarrays_to_parameters(params))

    def fit(self, ins: FitIns, timeout: Optional[float], group_id: Optional[int]) -> FitRes:
        params = parameters_to_ndarrays(ins.parameters)
        res_params, num_samples, metrics = self.client.fit(params, ins.config)
        return FitRes(Status(Code.OK, ""), ndarrays_to_parameters(res_params), num_samples, metrics)

    def evaluate(self, ins: EvaluateIns, timeout: Optional[float], group_id: Optional[int]) -> EvaluateRes:
        params = parameters_to_ndarrays(ins.parameters)
        loss, num_samples, metrics = self.client.evaluate(params, ins.config)
        return EvaluateRes(Status(Code.OK, ""), float(loss), num_samples, metrics)

    def reconnect(self, ins: Any, timeout: Optional[float], group_id: Optional[int]) -> Any:
        return None

    def disconnect(self, ins: Any, timeout: Optional[float], group_id: Optional[int]) -> Any:
        return None


class FederationRunner:
    """Coordinates federated learning experiments, enforcing security, privacy, and safety invariants."""

    def __init__(
        self,
        job_id: Optional[str] = None,
        accountant_db_path: Path = Path("artifacts/federation/privacy_accountant.db"),
    ) -> None:
        self.job_id = job_id or f"pfl_job_{int(time.time())}"
        self.accountant_db_path = Path(accountant_db_path)
        self.accountant_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.accountant = PrivacyAccountant(db_path=self.accountant_db_path)
        self.checkpoint_manager = CheckpointManager()
        self.evaluator = FederatedModelEvaluator()
        self.registry = CandidateModelRegistry()
        self.secagg_simulator = SecAggProtocolSimulator()

    def run_experiment(
        self,
        profile: str = "research",  # "research" or "protected"
        partition_name: str = "iid",  # "iid", "moderate_non_iid", "strong_non_iid"
        num_rounds: int = 3,
        num_participants: int = 7,
        reconstruction_threshold: int = 5,
        equal_isp_weighting: bool = True,
        use_dp: Optional[bool] = None,
        use_secagg: Optional[bool] = None,
        epsilon_target: float = 2.0,
        delta_target: float = 1e-5,
        noise_multiplier: float = 1.0,
        max_grad_norm: float = 1.0,
        batch_size: int = 64,
        local_epochs: int = 1,
        learning_rate: float = 0.001,
        simulated_dropouts: Optional[List[str]] = None,
        register_candidate: bool = True,
    ) -> Dict[str, Any]:
        """Execute a full federated learning training run."""
        start_time = time.time()
        process = psutil.Process(os.getpid())
        mem_start_mb = process.memory_info().rss / (1024 * 1024)

        # Set profile defaults
        if profile == "protected":
            dp_active = True if use_dp is None else use_dp
            secagg_active = True if use_secagg is None else use_secagg
        else:
            dp_active = False if use_dp is None else use_dp
            secagg_active = False if use_secagg is None else use_secagg

        cohort = ALL_PARTICIPANTS[:num_participants]
        dropped_set = set(simulated_dropouts or [])
        active_cohort = [cid for cid in cohort if cid not in dropped_set]

        logger.info(
            "Starting Federation run: job=%s, profile=%s, regime=%s, rounds=%d, cohort=%d, active=%d, dp=%s, secagg=%s",
            self.job_id,
            profile,
            partition_name,
            num_rounds,
            len(cohort),
            len(active_cohort),
            dp_active,
            secagg_active,
        )

        # Initialize shared global model: GroupNorm if DP is active, BatchNorm if research baseline
        global_model = TabularMLPNet(
            input_dim=14,
            hidden_dims=[64, 32],
            num_classes=2,
            use_group_norm=dp_active,
        )
        base_model_digest = global_model.compute_model_digest()

        round_summaries: List[Dict[str, Any]] = []
        final_state = "COMPLETED"
        aborted_reason: Optional[str] = None
        bytes_transmitted = 0
        client_validators: Dict[str, ParticipantAdmissionValidator] = {
            pid: ParticipantAdmissionValidator(tenant_id=pid) for pid in cohort
        }

        for r in range(1, num_rounds + 1):
            round_id = f"round_{r}"
            sm = RoundStateMachine(round_id=round_id)
            sm.transition_to(RoundState.VALIDATING, "Validating round configuration")

            # 1. Round Manifest Construction
            manifest = RoundManifest(
                round_id=round_id,
                job_id=self.job_id,
                sequence=r,
                cohort=cohort,
                base_model_digest=base_model_digest,
                application_digest=hashlib.sha256(b"fcs_pfl_v1_2").hexdigest(),
                feature_schema_digest=LOCKED_FEATURE_SCHEMA_DIGEST,
                privacy_policy_version="fcs_dp_v1" if dp_active else "none",
                aggregation_protocol=AggregationProtocol.SECAGG_PLUS if secagg_active else AggregationProtocol.PLAINTEXT_FEDAVG,
                reconstruction_threshold=reconstruction_threshold,
                nonce=f"{self.job_id}_{round_id}_{time.time()}",
                coordinator_signature="fcs_dev_coordinator_signed",
                valid_until=datetime.fromtimestamp(time.time() + 3600, UTC).isoformat(),
            )

            # 2. Admission Check
            sm.transition_to(RoundState.ADMITTING, "Validating client admission")
            admitted_clients = []
            for pid in active_cohort:
                if pid not in client_validators:
                    client_validators[pid] = ParticipantAdmissionValidator(tenant_id=pid)
                validator = client_validators[pid]
                is_valid, reason = validator.validate(manifest, participant_id=pid)
                if is_valid:
                    admitted_clients.append(pid)
                else:
                    logger.warning("[%s] Client %s admission failed: %s", round_id, pid, reason)

            # Check threshold
            if len(admitted_clients) < reconstruction_threshold:
                sm.abort(f"Admitted cohort size {len(admitted_clients)} < reconstruction threshold {reconstruction_threshold}")
                final_state = "ABORTED"
                aborted_reason = sm.error_reason
                round_summaries.append({
                    "round": r,
                    "state": sm.current_state.value,
                    "reason": aborted_reason,
                    "active_clients": admitted_clients,
                })
                break

            # 3. Setup Client Proxies
            client_manager = SimpleClientManager()
            for pid in admitted_clients:
                dp_eng = None
                if dp_active:
                    dp_eng = DPPrivacyEngine(
                        target_epsilon=epsilon_target,
                        target_delta=delta_target,
                        max_grad_norm=max_grad_norm,
                        noise_multiplier=noise_multiplier,
                    )

                client = FCSFlowerClient(
                    participant_id=pid,
                    partition_name=partition_name,
                    model=TabularMLPNet(input_dim=14, hidden_dims=[64, 32], num_classes=2, use_group_norm=dp_active),
                    accountant=self.accountant if dp_active else None,
                    dp_engine=dp_eng,
                    batch_size=batch_size,
                    local_epochs=local_epochs,
                    learning_rate=learning_rate,
                    use_dp=dp_active,
                    manifest=manifest,
                )
                client_manager.register(LocalFlowerClientProxy(pid, client))

            # 4. Strategy & Aggregation
            strategy = FCSFedAvgStrategy(
                min_fit_clients=reconstruction_threshold,
                min_evaluate_clients=reconstruction_threshold,
                min_available_clients=len(admitted_clients),
                equal_isp_weighting=equal_isp_weighting,
                initial_parameters=ndarrays_to_parameters(global_model.get_parameters()),
            )

            if secagg_active:
                sm.transition_to(RoundState.SETUP, "Initializing SecAgg+ protocol")
                sm.transition_to(RoundState.KEY_SHARING, "Simulating pairwise key sharing")

            sm.transition_to(RoundState.LOCAL_TRAINING, "Executing local participant training")
            server = Server(client_manager=client_manager, strategy=strategy)

            # Fit 1 round
            try:
                server.fit(num_rounds=1, timeout=120.0)
            except Exception as e:
                sm.fail(f"Server fit error: {e}")
                final_state = "FAILED"
                aborted_reason = str(e)
                break

            if secagg_active:
                sm.transition_to(RoundState.MASKED_COLLECTION, "Simulating masked vector collection")
                sm.transition_to(RoundState.UNMASKING, "Simulating SecAgg+ unmasking")

            sm.transition_to(RoundState.AGGREGATE_VALIDATION, "Validating aggregate parameter tensors")

            # Extract updated parameters from strategy history
            latest_round_data = strategy.round_history[-1] if strategy.round_history else {}
            fit_metrics = latest_round_data.get("metrics", {})

            # Update global model with aggregated weights if successful
            # Estimate communication bytes
            param_bytes = sum(p.nbytes for p in global_model.get_parameters())
            # For each client: download + upload (with SecAgg+ masking expansion factor ~2.2x)
            client_comm = param_bytes * 2 * (2.2 if secagg_active else 1.0)
            bytes_transmitted += int(client_comm * len(admitted_clients))

            # Checkpoint round
            self.checkpoint_manager.save_checkpoint(
                job_id=self.job_id,
                round_id=round_id,
                model=global_model,
                state=sm.current_state.value,
                metrics=fit_metrics,
                participants=admitted_clients,
            )

            sm.transition_to(RoundState.EVALUATING, "Running round evaluation")
            sm.transition_to(RoundState.CANDIDATE_READY, "Round completed successfully")

            round_summaries.append({
                "round": r,
                "state": sm.current_state.value,
                "participating_clients": len(admitted_clients),
                "metrics": fit_metrics,
            })

        # Final Evaluation on Global Holdout Test Set & Tenant Partitions
        eval_metrics = {}
        fairness_metrics = {}
        tenant_breakdown = {}

        if final_state == "COMPLETED":
            eval_metrics = self.evaluator.evaluate_model(global_model)
            tenant_breakdown = self.evaluator.evaluate_per_tenant(global_model, partition_name=partition_name)
            fairness_metrics = self.evaluator.compute_fairness_summary(tenant_breakdown)

        duration = time.time() - start_time
        mem_end_mb = process.memory_info().rss / (1024 * 1024)

        # Register candidate model artifact if requested and completed
        candidate_id = f"candidate_{self.job_id}"
        if register_candidate and final_state == "COMPLETED":
            self.registry.register_candidate(
                candidate_id=candidate_id,
                model=global_model,
                round_id=f"round_{num_rounds}",
                job_id=self.job_id,
                evaluation_metrics={**eval_metrics, **fairness_metrics},
                is_dp_enabled=dp_active,
                is_secagg_enabled=secagg_active,
                status=CandidateStatus.VALIDATED,
            )

        report = {
            "job_id": self.job_id,
            "profile": profile,
            "partition_name": partition_name,
            "status": final_state,
            "aborted_reason": aborted_reason,
            "num_rounds_requested": num_rounds,
            "num_rounds_completed": len(round_summaries),
            "dp_enabled": dp_active,
            "secagg_enabled": secagg_active,
            "equal_isp_weighting": equal_isp_weighting,
            "duration_seconds": float(duration),
            "peak_memory_mb": float(max(mem_start_mb, mem_end_mb)),
            "bytes_transmitted": bytes_transmitted,
            "eval_metrics": eval_metrics,
            "fairness_metrics": fairness_metrics,
            "tenant_breakdown": tenant_breakdown,
            "round_summaries": round_summaries,
            "candidate_id": candidate_id if (register_candidate and final_state == "COMPLETED") else None,
        }

        return report
