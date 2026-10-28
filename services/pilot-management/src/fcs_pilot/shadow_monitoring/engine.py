"""Server-enforced Shadow Monitoring Engine for FCS Phase 9."""

import logging
from datetime import UTC, datetime
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger("fcs_pilot.shadow_monitoring")


class ShadowIncidentCandidate(BaseModel):
    """Candidate threat incident generated in Shadow Mode."""
    candidate_id: str
    tenant_id: str
    exporter_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    attack_class: str
    anomaly_score: float
    confidence: float
    evidence: dict[str, Any]
    advisory_recommendation: dict[str, Any]
    is_shadow_mode: bool = True
    action_executed: bool = False  # Strictly False in shadow mode


class ShadowMonitoringEngine:
    """
    Executes telemetry analysis and model inference in strictly server-enforced Shadow Mode.
    Guarantees:
    1. Zero live firewall or router control commands can be dispatched.
    2. All generated recommendations are marked ADVISORY_ONLY.
    3. Auto Response (AUTO) remains permanently disabled.
    4. Tenant data remains strictly within tenant boundaries.
    """

    def __init__(self, tenant_id: str, shadow_mode_enabled: bool = True) -> None:
        self.tenant_id = tenant_id
        self.shadow_mode_enabled = shadow_mode_enabled
        self._candidate_incidents: list[ShadowIncidentCandidate] = []
        self._total_flows_ingested = 0
        self._total_windows_scored = 0

    def process_telemetry_window(
        self,
        exporter_id: str,
        window_features: dict[str, Any],
        model_score_fn: Any | None = None,
    ) -> ShadowIncidentCandidate | None:
        """
        Process an aggregated telemetry feature window, score via model/heuristics,
        and generate an advisory incident if threat threshold is exceeded.
        """
        if not self.shadow_mode_enabled:
            raise RuntimeError("ShadowMonitoringEngine must operate with shadow_mode_enabled=True.")

        self._total_windows_scored += 1
        flow_count = window_features.get("packet_count", window_features.get("IN_PKTS", 100))
        self._total_flows_ingested += int(flow_count)

        # 1. Model inference or heuristic evaluation
        attack_class = "NORMAL"
        anomaly_score = 0.05
        confidence = 0.98

        if model_score_fn is not None:
            try:
                score_res = model_score_fn(window_features)
                anomaly_score = score_res.get("anomaly_score", 0.05)
                attack_class = score_res.get("attack_class", "NORMAL")
                confidence = score_res.get("confidence", 0.9)
            except Exception as e:
                logger.warning(f"Model inference failed, falling back to rule heuristic: {e}")
                attack_class, anomaly_score, confidence = self._rule_heuristic(window_features)
        else:
            attack_class, anomaly_score, confidence = self._rule_heuristic(window_features)

        # 2. Check if candidate incident should be created
        if anomaly_score >= 0.70 or attack_class != "NORMAL":
            cand_id = f"cand-{self.tenant_id[:5]}-{self._total_windows_scored:05d}"
            target_ip = window_features.get("dst_ip", window_features.get("destinationIPv4Address", "192.168.1.100"))
            src_ip = window_features.get("src_ip", window_features.get("sourceIPv4Address", "203.0.113.55"))

            candidate = ShadowIncidentCandidate(
                candidate_id=cand_id,
                tenant_id=self.tenant_id,
                exporter_id=exporter_id,
                attack_class=attack_class,
                anomaly_score=round(anomaly_score, 4),
                confidence=round(confidence, 4),
                evidence={
                    "window_features": window_features,
                    "target_ip": target_ip,
                    "suspicious_source": src_ip,
                    "evaluated_by": "FCS-HMD-ShadowDetector-v1.2",
                },
                advisory_recommendation={
                    "action_type": "TEMPORARY_BLOCK",
                    "target": src_ip,
                    "duration_seconds": 300,
                    "risk_level": "LOW" if anomaly_score < 0.85 else "MEDIUM",
                    "execution_status": "ADVISORY_ONLY_NOT_EXECUTED",
                    "reason": f"Shadow detection identified suspected {attack_class} with score {anomaly_score:.2f}",
                },
                is_shadow_mode=True,
                action_executed=False,  # Strict invariant
            )
            self._candidate_incidents.append(candidate)
            return candidate

        return None

    def _rule_heuristic(self, features: dict[str, Any]) -> tuple[str, float, float]:
        """Deterministic rule heuristics for fallback or synthetic replay."""
        in_pkts = float(features.get("IN_PKTS", features.get("packet_count", 0)))
        in_bytes = float(features.get("IN_BYTES", features.get("byte_count", 0)))
        tcp_flags = int(features.get("TCP_FLAGS", features.get("tcp_flags", 0)))
        proto = int(features.get("PROTOCOL", features.get("protocol", 6)))

        # SYN Flood pattern: high packet count, small bytes, TCP SYN (0x02)
        if proto == 6 and (tcp_flags & 0x02) and not (tcp_flags & 0x10) and in_pkts > 500:
            return "SYN_FLOOD", 0.94, 0.96

        # DNS Amplification pattern: UDP (17), port 53, large bytes/pkt ratio
        if proto == 17 and in_bytes > 50000 and in_pkts > 100:
            return "DNS_AMPLIFICATION", 0.91, 0.93

        # Volumetric DDoS
        if in_pkts > 10000 or in_bytes > 10000000:
            return "VOLUMETRIC_DDOS", 0.98, 0.99

        return "NORMAL", 0.05, 0.98

    def get_candidate_incidents(self) -> list[ShadowIncidentCandidate]:
        return list(self._candidate_incidents)

    def get_metrics(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "shadow_mode_enabled": self.shadow_mode_enabled,
            "total_flows_ingested": self._total_flows_ingested,
            "total_windows_scored": self._total_windows_scored,
            "candidate_incidents_generated": len(self._candidate_incidents),
            "network_action_executed": False,  # Strict invariant
        }
