"""Traffic replay tools for deterministic offline verification."""

from dataclasses import dataclass

from services.telemetry_collector.collector import TelemetryCollector
from tools.synthetic_exporter.generator import SyntheticPacket


@dataclass
class ReplaySummary:
    """Summary of replayed telemetry packets and accepted events."""

    total_packets_sent: int
    accepted_events_count: int
    rejected_events_count: int
    elapsed_seconds: float


class TrafficReplayer:
    """Replays synthetic IPFIX packet streams into a TelemetryCollector instance."""

    def __init__(self, collector: TelemetryCollector) -> None:
        self.collector = collector

    def replay_packets(
        self,
        packets: list[SyntheticPacket],
        source_ip: str = "10.100.1.1",
        boot_epoch: int = 0,
    ) -> ReplaySummary:
        """Replay a sequence of synthetic packets through the collector pipeline."""
        accepted = 0
        import time

        start_t = time.perf_counter()

        for pkt in packets:
            events = self.collector.process_packet(
                packet_bytes=pkt.raw_bytes,
                source_ip=source_ip,
                boot_epoch=boot_epoch,
            )
            accepted += len(events)

        elapsed = time.perf_counter() - start_t

        return ReplaySummary(
            total_packets_sent=len(packets),
            accepted_events_count=accepted,
            rejected_events_count=max(0, len(packets) - accepted),
            elapsed_seconds=elapsed,
        )
