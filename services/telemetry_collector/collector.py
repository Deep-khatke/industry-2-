"""High-level Telemetry Collector engine coordinating parsing, tenancy, metrics, and streaming."""

import socket
import threading
from dataclasses import dataclass

from adapters.base import StreamSink
from packages.contracts.flow_event import FlowEvent
from packages.observability.coverage import CoverageTracker
from packages.observability.logger import StructuredLogger, get_logger
from packages.observability.metrics import MetricsCollector
from packages.tenancy.exceptions import UntrustedTenantClaimViolation
from packages.tenancy.registry import TenantRegistry

from .normalizer import TelemetryNormalizer
from .protocol import IPFIXParser, ProtocolError
from .sequence import SequenceTracker
from .templates import TemplateCache


@dataclass
class CollectorConfig:
    """Runtime configuration for the telemetry collector."""

    host: str = "127.0.0.1"
    port: int = 2055
    max_packet_size_bytes: int = 65507
    max_buffered_records: int = 50000


class TelemetryCollector:
    """
    Zero-Cost telemetry ingestion engine for rural ISP networks.
    Enforces strict tenant isolation, memory bounds, and fault-tolerant parsing.
    """

    def __init__(
        self,
        tenant_registry: TenantRegistry,
        stream_sink: StreamSink,
        metrics: MetricsCollector | None = None,
        coverage: CoverageTracker | None = None,
        config: CollectorConfig | None = None,
    ) -> None:
        self.registry = tenant_registry
        self.sink = stream_sink
        self.metrics = metrics or MetricsCollector()
        self.coverage = coverage or CoverageTracker()
        self.config = config or CollectorConfig()
        self.logger: StructuredLogger = get_logger("fcs.collector")

        self.templates = TemplateCache()
        self.sequences = SequenceTracker()
        self._running = False
        self._socket: socket.socket | None = None
        self._listener_thread: threading.Thread | None = None

    def process_packet(
        self,
        packet_bytes: bytes,
        source_ip: str,
        boot_epoch: int = 0,
    ) -> list[FlowEvent]:
        """
        Process a single raw UDP packet received from a network interface or test fixture.
        Returns list of successfully accepted, normalized FlowEvents.
        """
        self.metrics.increment("packets_received")

        # 1. Enforce physical UDP payload memory limits
        if len(packet_bytes) > self.config.max_packet_size_bytes:
            self.metrics.increment("events_rejected")
            self.metrics.increment("packets_corrupted")
            self.logger.warning(
                "Packet exceeded maximum allowable size limit",
                size=len(packet_bytes),
                max_allowed=self.config.max_packet_size_bytes,
                source_ip=source_ip,
            )
            return []

        # 2. Parse protocol message header
        try:
            header = IPFIXParser.parse_header(packet_bytes)
        except ProtocolError as e:
            self.metrics.increment("events_rejected")
            self.metrics.increment("packets_corrupted")
            self.logger.warning("Failed to decode telemetry header", error=str(e), source_ip=source_ip)
            return []

        # 3. Resolve trusted tenant boundary from pre-registered exporter lookup
        resolved = self.registry.resolve_exporter(
            exporter_ip=source_ip,
            observation_domain_id=header.observation_domain_id,
        )
        if resolved is None:
            self.metrics.increment("events_rejected")
            self.metrics.increment("tenant_scope_violations")
            self.logger.warning(
                "Rejected telemetry from unregistered exporter or domain",
                source_ip=source_ip,
                domain_id=header.observation_domain_id,
            )
            return []

        trusted_tenant_id, exporter_id = resolved

        # 4. Sequence tracking and packet loss / gap detection
        seq_status = self.sequences.track_sequence(
            exporter_ip=source_ip,
            observation_domain_id=header.observation_domain_id,
            received_sequence=header.sequence_number,
            records_in_packet=1,
            boot_epoch=boot_epoch,
        )

        if seq_status.is_gap:
            self.metrics.increment("sequence_gaps", value=seq_status.gap_size)
            self.coverage.record_activity(
                tenant_id=trusted_tenant_id,
                exporter_id=exporter_id,
                sequence_gaps=seq_status.gap_size,
            )
            self.logger.warning(
                "Observable sequence gap detected in telemetry stream",
                tenant_id=trusted_tenant_id,
                exporter_id=exporter_id,
                gap_size=seq_status.gap_size,
                expected=seq_status.expected_sequence,
                received=seq_status.received_sequence,
            )

        if seq_status.is_duplicate_or_reorder:
            self.metrics.increment("duplicate_events")

        # 5. Parse Sets and extract data records using exporter-isolated template state
        active_templates = self.templates.get_templates_for_domain(
            exporter_ip=source_ip,
            observation_domain_id=header.observation_domain_id,
        )

        try:
            parsed = IPFIXParser.parse_sets(
                buffer=packet_bytes,
                header=header,
                template_lookup=active_templates,
            )
        except ProtocolError as e:
            self.metrics.increment("events_rejected")
            self.metrics.increment("processing_failures")
            self.logger.warning("Error parsing IPFIX sets", error=str(e), source_ip=source_ip)
            return []

        # Update cached templates
        for tmpl in parsed.new_templates:
            self.templates.store_template(
                exporter_ip=source_ip,
                observation_domain_id=header.observation_domain_id,
                template=tmpl,
            )

        accepted_events: list[FlowEvent] = []

        # 6. Normalize decoded data records
        for template_id, records in parsed.data_sets:
            if not records and template_id >= 256:
                # Unknown template referenced by data set
                self.metrics.increment("invalid_templates")
                self.logger.warning(
                    "Data record arrived for unregistered template ID",
                    template_id=template_id,
                    exporter_id=exporter_id,
                )
                continue

            for idx, raw_record in enumerate(records):
                try:
                    event = TelemetryNormalizer.normalize_record(
                        raw_fields=raw_record,
                        trusted_tenant_id=trusted_tenant_id,
                        exporter_id=exporter_id,
                        observation_domain=header.observation_domain_id,
                        boot_epoch=boot_epoch,
                        sequence=header.sequence_number + idx,
                        export_time_seconds=header.export_time,
                    )
                    accepted_events.append(event)
                except UntrustedTenantClaimViolation as e:
                    self.metrics.increment("tenant_scope_violations")
                    self.metrics.increment("events_rejected")
                    self.logger.error("Security violation: Untrusted tenant claim rejected", error=str(e))
                except Exception as e:
                    self.metrics.increment("events_rejected")
                    self.metrics.increment("processing_failures")
                    self.logger.warning("Record normalization failed", error=str(e))

        # 7. Write accepted events to stream sink
        if accepted_events:
            try:
                self.sink.write_batch(accepted_events)
                self.metrics.increment("events_accepted", value=len(accepted_events))
                self.coverage.record_activity(
                    tenant_id=trusted_tenant_id,
                    exporter_id=exporter_id,
                    sequence_gaps=0,
                )
            except Exception as e:
                self.metrics.increment("stream_write_failures", value=len(accepted_events))
                self.logger.error("Failed to write flow events to stream sink", error=str(e))

        return accepted_events

    def start_udp_listener(self) -> None:
        """Start non-blocking UDP server on configured host and port (ephemeral development use)."""
        if self._running:
            return
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind((self.config.host, self.config.port))
        self._socket.settimeout(0.5)
        self._running = True

        def _listen() -> None:
            while self._running:
                try:
                    if self._socket is None:
                        break
                    data, addr = self._socket.recvfrom(self.config.max_packet_size_bytes)
                    self.process_packet(data, source_ip=addr[0])
                except TimeoutError:
                    continue
                except OSError:
                    break

        self._listener_thread = threading.Thread(target=_listen, daemon=True)
        self._listener_thread.start()

    def stop_udp_listener(self) -> None:
        """Stop UDP listener and clean up socket."""
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=1.0)
