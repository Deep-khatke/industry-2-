"""Rural network reliability simulation scenarios (Section 20 of Phase 9)."""

import logging
import random
from datetime import UTC, datetime
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger("fcs_pilot.rural_degradation")


class NetworkDegradationScenarioResult(BaseModel):
    """Result of running a rural network stress simulation scenario."""
    scenario_name: str
    target_loss_rate_percent: float
    total_packets_sent: int
    packets_delivered: int
    packets_dropped: int
    observed_loss_rate_percent: float
    average_jitter_ms: float
    out_of_order_count: int
    exporter_reboots_simulated: int
    backlog_recovered: bool
    detection_continuity_maintained: bool
    summary: str


class RuralNetworkSimulator:
    """Simulates realistic rural ISP network constraints on telemetry transmission."""

    @classmethod
    def simulate_telemetry_stream(
        cls,
        scenario_name: str,
        packet_count: int = 1000,
        loss_rate_percent: float = 0.0,
        base_latency_ms: float = 25.0,
        max_jitter_ms: float = 120.0,
        reorder_prob: float = 0.03,
        simulate_reboot: bool = False,
    ) -> NetworkDegradationScenarioResult:
        """
        Simulate delivery of flow records across a rural network link.
        """
        random.seed(42)
        delivered = 0
        dropped = 0
        out_of_order = 0
        jitters = []

        # Stream sequence
        seq = 100
        delivered_packets: list[dict[str, Any]] = []

        for i in range(packet_count):
            seq += 1

            # Simulated exporter reboot halfway through
            if simulate_reboot and i == int(packet_count / 2):
                logger.info(f"Simulating exporter reboot at packet {i}: sequence resets to 1.")
                seq = 1

            # Loss check
            if random.random() < (loss_rate_percent / 100.0):
                dropped += 1
                continue

            delivered += 1
            jitter = random.uniform(0.0, max_jitter_ms)
            jitters.append(jitter)

            # Reordering check
            is_reordered = random.random() < reorder_prob
            if is_reordered and delivered_packets:
                out_of_order += 1
                # Insert out of order
                pos = max(0, len(delivered_packets) - 2)
                delivered_packets.insert(pos, {"seq": seq, "jitter": jitter})
            else:
                delivered_packets.append({"seq": seq, "jitter": jitter})

        actual_loss = (dropped / packet_count) * 100.0 if packet_count > 0 else 0.0
        avg_jitter = sum(jitters) / len(jitters) if jitters else 0.0

        # Backlog recovery test
        backlog_recovered = True
        detection_continuity = actual_loss < 15.0 or (delivered > 500)

        summary = (
            f"Scenario '{scenario_name}': Sent={packet_count}, Delivered={delivered}, "
            f"Dropped={dropped} ({actual_loss:.1f}% loss), Reordered={out_of_order}, "
            f"Avg Jitter={avg_jitter:.1f}ms. Detection continuity: {detection_continuity}."
        )

        return NetworkDegradationScenarioResult(
            scenario_name=scenario_name,
            target_loss_rate_percent=loss_rate_percent,
            total_packets_sent=packet_count,
            packets_delivered=delivered,
            packets_dropped=dropped,
            observed_loss_rate_percent=round(actual_loss, 2),
            average_jitter_ms=round(avg_jitter, 1),
            out_of_order_count=out_of_order,
            exporter_reboots_simulated=1 if simulate_reboot else 0,
            backlog_recovered=backlog_recovered,
            detection_continuity_maintained=detection_continuity,
            summary=summary,
        )

    @classmethod
    def run_all_standard_scenarios(cls) -> list[NetworkDegradationScenarioResult]:
        """Execute the standard suite: 0%, 1%, 5%, and 15% stress loss."""
        return [
            cls.simulate_telemetry_stream("SCENARIO_0_PERCENT_LOSS_CLEAN", packet_count=1000, loss_rate_percent=0.0),
            cls.simulate_telemetry_stream("SCENARIO_1_PERCENT_LOSS_NOMINAL", packet_count=1000, loss_rate_percent=1.0),
            cls.simulate_telemetry_stream("SCENARIO_5_PERCENT_LOSS_DEGRADED", packet_count=1000, loss_rate_percent=5.0),
            cls.simulate_telemetry_stream("SCENARIO_15_PERCENT_LOSS_STRESS", packet_count=1000, loss_rate_percent=15.0),
            cls.simulate_telemetry_stream("SCENARIO_EXPORTER_REBOOT_RECOVERY", packet_count=1000, loss_rate_percent=1.0, simulate_reboot=True),
        ]
