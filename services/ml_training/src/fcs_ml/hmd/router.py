"""Conditional Model Router for FCS-HMD Hierarchical Threat Detection."""

import time
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from fcs_ml.models.botnet_specialist import assess_botnet_eligibility
from packages.contracts.model_score import ModelScore


class RoutingDecision(BaseModel):
    """Structured record of a conditional routing decision."""

    decision_id: str = Field(default_factory=lambda: f"route_{uuid.uuid4().hex[:10]}")
    tenant_id: str
    window_id: str | None = None
    level1_general_score: float
    level1_anomaly_score: float
    should_route_specialists: bool
    routed_models: list[str] = Field(default_factory=list)
    bypassed_models: list[str] = Field(default_factory=list)
    trigger_reasons: list[str] = Field(default_factory=list)
    routing_latency_us: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ConditionalModelRouter:
    """
    Evaluates Level 1 threat and anomaly indicators to conditionally route
    specialist attack models or short-circuit normal traffic to save CPU budget.
    """

    def __init__(
        self,
        general_routing_threshold: float = 0.35,
        anomaly_routing_threshold: float = 0.40,
        enable_ddos_specialist: bool = True,
        enable_scanning_specialist: bool = True,
        enable_botnet_specialist: bool = False,
    ) -> None:
        self.general_routing_threshold = general_routing_threshold
        self.anomaly_routing_threshold = anomaly_routing_threshold
        self.enable_ddos_specialist = enable_ddos_specialist
        self.enable_scanning_specialist = enable_scanning_specialist
        self.enable_botnet_specialist = enable_botnet_specialist

    def route(
        self,
        features: dict[str, Any],
        general_score: ModelScore,
        anomaly_score: ModelScore,
        flow_event: dict[str, Any] | None = None,
        flow_count: int = 1,
        tenant_id: str = "global",
        window_id: str | None = None,
    ) -> RoutingDecision:
        """
        Evaluate Level 1 scores and flow characteristics to decide specialist invocation.
        """
        start_t = time.perf_counter()

        in_bytes = float(features.get("IN_BYTES", 0))
        in_pkts = float(features.get("IN_PKTS", 0))
        tcp_flags = int(features.get("TCP_FLAGS", 0))
        dst_port = int(features.get("L4_DST_PORT", 0))
        duration_ms = float(features.get("FLOW_DURATION_MILLISECONDS", 100))

        gen_prob = general_score.calibrated_probability if general_score is not None else 0.0
        anom_prob = anomaly_score.calibrated_probability if anomaly_score is not None else 0.0

        # Check volumetric indicators
        has_volumetric_burst = (
            in_bytes > 200_000
            or in_pkts > 1_000
            or flow_count > 35
            or (duration_ms > 0 and (in_bytes / (duration_ms / 1000.0)) > 2_000_000)
        )

        # Check scanning / probe indicators (SYN probes with low packet count)
        is_syn_scan = (tcp_flags == 2 or (tcp_flags & 0x02 != 0 and tcp_flags & 0x10 == 0)) and (in_pkts < 10)
        is_probe_port = dst_port in {21, 22, 23, 25, 110, 143, 445, 1433, 2323, 3306, 3389, 5432}

        # Level 1 elevation check: General model, Anomaly model, or deterministic behavioral bursts
        elevated_level1 = (
            has_volumetric_burst
            or is_syn_scan
            or (anom_prob >= self.anomaly_routing_threshold and in_bytes > 20_000)
            or (gen_prob >= 0.65 and (is_probe_port or in_bytes > 30_000))
        )

        routed_models: list[str] = []
        bypassed_models: list[str] = []
        trigger_reasons: list[str] = []

        if not elevated_level1:
            # Short-circuit to Normal, bypass all specialists
            should_route = False
            bypassed_models = ["ddos_specialist", "scanning_specialist", "botnet_specialist"]
            trigger_reasons.append("BENIGN_BASELINE_SHORT_CIRCUIT: Level 1 threat and anomaly probabilities below routing thresholds")
        else:
            should_route = True

            # 1. Evaluate DDoS Specialist Eligibility & Trigger
            if self.enable_ddos_specialist:
                if has_volumetric_burst or (in_bytes > 30_000 and gen_prob >= 0.50) or anom_prob >= 0.75:
                    routed_models.append("ddos_specialist")
                    reason = "VOLUMETRIC_BURST" if has_volumetric_burst else "LEVEL1_THREAT_ELEVATION"
                    trigger_reasons.append(f"DDOS_SPECIALIST: {reason} (in_bytes={in_bytes:.0f}, in_pkts={in_pkts:.0f})")
                else:
                    bypassed_models.append("ddos_specialist")
            else:
                bypassed_models.append("ddos_specialist")

            # 2. Evaluate Scanning Specialist Eligibility & Trigger
            if self.enable_scanning_specialist:
                if is_syn_scan or (is_probe_port and gen_prob >= 0.40):
                    routed_models.append("scanning_specialist")
                    reason = "TCP_SYN_FLAG_DETECTED" if is_syn_scan else "PROBE_PORT_TARGETED"
                    trigger_reasons.append(f"SCANNING_SPECIALIST: {reason} (dst_port={dst_port}, tcp_flags={tcp_flags})")
                else:
                    bypassed_models.append("scanning_specialist")
            else:
                bypassed_models.append("scanning_specialist")

            # 3. Evaluate Botnet Specialist Eligibility
            botnet_check = assess_botnet_eligibility(list(features.keys()))
            if self.enable_botnet_specialist and botnet_check["is_eligible"]:
                routed_models.append("botnet_specialist")
                trigger_reasons.append("BOTNET_SPECIALIST: Features eligible and periodic pattern observed")
            else:
                bypassed_models.append("botnet_specialist")
                if not botnet_check["is_eligible"]:
                    trigger_reasons.append(f"BOTNET_SPECIALIST_BYPASSED: Ineligible ({', '.join(botnet_check['missing_prerequisites'])} missing)")

        latency_us = (time.perf_counter() - start_t) * 1_000_000.0

        return RoutingDecision(
            tenant_id=tenant_id,
            window_id=window_id,
            level1_general_score=gen_prob,
            level1_anomaly_score=anom_prob,
            should_route_specialists=should_route,
            routed_models=routed_models,
            bypassed_models=bypassed_models,
            trigger_reasons=trigger_reasons,
            routing_latency_us=latency_us,
        )
