"""Normalizer transforming raw IPFIX data records into privacy-preserving FlowEvents."""

import ipaddress
from datetime import UTC, datetime
from typing import Any

from packages.contracts.enums import FlowDirection, PortClass, TransportProtocol
from packages.contracts.flow_event import FlowEvent, compute_deterministic_event_id
from packages.tenancy.exceptions import UntrustedTenantClaimViolation

from .protocol import (
    IE_DESTINATION_IPV4_ADDRESS,
    IE_DESTINATION_TRANSPORT_PORT,
    IE_FLOW_DIRECTION,
    IE_FLOW_END_MILLISECONDS,
    IE_FLOW_START_MILLISECONDS,
    IE_OCTET_DELTA_COUNT,
    IE_PACKET_DELTA_COUNT,
    IE_PROTOCOL_IDENTIFIER,
    IE_SOURCE_IPV4_ADDRESS,
    IE_SOURCE_TRANSPORT_PORT,
    IE_TCP_CONTROL_BITS,
)


class TelemetryNormalizer:
    """Transforms protocol field dictionaries into normalized, privacy-masked FlowEvent objects."""

    @staticmethod
    def mask_ip_prefix(ip_str: str | None) -> str | None:
        """Mask subscriber host portion to /24 for IPv4, preserving subnet anonymity."""
        if not ip_str or ip_str == "0.0.0.0":
            return None
        try:
            ip = ipaddress.ip_address(ip_str)
            if ip.version == 4:
                network = ipaddress.ip_network(f"{ip_str}/24", strict=False)
                return str(network)
            elif ip.version == 6:
                network = ipaddress.ip_network(f"{ip_str}/48", strict=False)
                return str(network)
        except ValueError:
            pass
        return None

    @classmethod
    def normalize_record(
        cls,
        raw_fields: dict[int, Any],
        trusted_tenant_id: str,
        exporter_id: str,
        observation_domain: int,
        boot_epoch: int,
        sequence: int,
        export_time_seconds: int,
        sample_rate: int = 1,
    ) -> FlowEvent:
        """Normalize a single data record dictionary into a canonical FlowEvent."""
        # Detect and reject untrusted tenant claims if present in vendor-specific fields
        claimed_tenant = raw_fields.get(9999)  # Hypothetical untrusted field
        if claimed_tenant is not None and str(claimed_tenant) != trusted_tenant_id:
            raise UntrustedTenantClaimViolation(
                claimed_tenant_id=str(claimed_tenant),
                trusted_tenant_id=trusted_tenant_id,
                exporter_id=exporter_id,
            )

        # Protocol mapping
        proto_num = int(raw_fields.get(IE_PROTOCOL_IDENTIFIER, 0))
        protocol = TransportProtocol.from_iana_number(proto_num)

        # Port mapping and classification
        src_port = raw_fields.get(IE_SOURCE_TRANSPORT_PORT)
        dst_port = raw_fields.get(IE_DESTINATION_TRANSPORT_PORT)
        src_port_int = int(src_port) if src_port is not None else None
        dst_port_int = int(dst_port) if dst_port is not None else None
        port_class = PortClass.classify(dst_port_int)

        # Direction mapping (0 = ingress/inbound, 1 = egress/outbound)
        dir_val = raw_fields.get(IE_FLOW_DIRECTION)
        if dir_val == 0:
            direction = FlowDirection.INBOUND
        elif dir_val == 1:
            direction = FlowDirection.OUTBOUND
        else:
            direction = FlowDirection.UNKNOWN

        # Counters
        bytes_count = int(raw_fields.get(IE_OCTET_DELTA_COUNT, 0))
        packets_count = int(raw_fields.get(IE_PACKET_DELTA_COUNT, 0))

        # Duration & timestamps
        start_ms = raw_fields.get(IE_FLOW_START_MILLISECONDS)
        end_ms = raw_fields.get(IE_FLOW_END_MILLISECONDS)
        if start_ms and end_ms and end_ms >= start_ms:
            duration_ms = int(end_ms - start_ms)
        else:
            duration_ms = 0

        if export_time_seconds > 0:
            event_time = datetime.fromtimestamp(export_time_seconds, tz=UTC)
        else:
            event_time = datetime.now(UTC)

        # IP prefix privacy preservation
        src_raw = raw_fields.get(IE_SOURCE_IPV4_ADDRESS)
        dst_raw = raw_fields.get(IE_DESTINATION_IPV4_ADDRESS)
        src_masked = cls.mask_ip_prefix(str(src_raw) if src_raw else None)
        dst_masked = cls.mask_ip_prefix(str(dst_raw) if dst_raw else None)

        # TCP flags
        tcp_flags = raw_fields.get(IE_TCP_CONTROL_BITS)
        tcp_flags_int = int(tcp_flags) if tcp_flags is not None else None

        event_id = compute_deterministic_event_id(
            tenant_id=trusted_tenant_id,
            exporter_id=exporter_id,
            observation_domain=observation_domain,
            boot_epoch=boot_epoch,
            sequence=sequence,
        )

        return FlowEvent(
            schema_version="1.0.0",
            event_id=event_id,
            tenant_id=trusted_tenant_id,
            exporter_id=exporter_id,
            observation_domain=observation_domain,
            boot_epoch=boot_epoch,
            sequence=sequence,
            event_time=event_time,
            ingest_time=datetime.now(UTC),
            sample_rate=sample_rate,
            protocol=protocol,
            port_class=port_class,
            src_port=src_port_int,
            dst_port=dst_port_int,
            direction=direction,
            byte_count=bytes_count,
            packet_count=packets_count,
            flow_duration_ms=duration_ms,
            tcp_flags=tcp_flags_int,
            src_prefix_masked=src_masked,
            dst_prefix_masked=dst_masked,
        )
