"""Synthetic network traffic generator for IPFIX telemetry and fault injection."""

import random
import socket
import struct
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from services.telemetry_collector.protocol import (
    IE_DESTINATION_IPV4_ADDRESS,
    IE_DESTINATION_TRANSPORT_PORT,
    IE_FLOW_DIRECTION,
    IE_OCTET_DELTA_COUNT,
    IE_PACKET_DELTA_COUNT,
    IE_PROTOCOL_IDENTIFIER,
    IE_SOURCE_IPV4_ADDRESS,
    IE_SOURCE_TRANSPORT_PORT,
    IE_TCP_CONTROL_BITS,
)


class TrafficScenario(StrEnum):
    """Pre-defined synthetic traffic scenario profiles."""

    NORMAL_RESIDENTIAL = "normal_residential"
    NORMAL_ENTERPRISE = "normal_enterprise"
    SEQUENCE_GAP_FAULT = "sequence_gap_fault"
    DUPLICATE_FLOW_FAULT = "duplicate_flow_fault"
    EXPORTER_RESTART_FAULT = "exporter_restart_fault"
    CORRUPTED_PACKET_FAULT = "corrupted_packet_fault"
    UNKNOWN_TEMPLATE_FAULT = "unknown_template_fault"
    UNTRUSTED_TENANT_CLAIM = "untrusted_tenant_claim"


@dataclass
class SyntheticPacket:
    """Wrapper around raw binary packet and metadata."""

    raw_bytes: bytes
    sequence_number: int
    is_corrupted: bool = False
    is_duplicate: bool = False
    scenario: str = "normal"


class SyntheticTrafficGenerator:
    """
    Deterministic synthetic IPFIX generator.
    Produces compliant binary packets and controlled fault scenarios for testing.
    """

    DEFAULT_TEMPLATE_ID = 256

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self._rng = random.Random(seed)

    def build_template_packet(
        self,
        observation_domain_id: int = 101,
        template_id: int = DEFAULT_TEMPLATE_ID,
        sequence_number: int = 1,
        export_time: int | None = None,
    ) -> bytes:
        """Construct a valid IPFIX Template Set message."""
        exp_time = export_time or int(time.time())

        # Standard 9-field template specifier list
        fields = [
            (IE_SOURCE_IPV4_ADDRESS, 4),
            (IE_DESTINATION_IPV4_ADDRESS, 4),
            (IE_PROTOCOL_IDENTIFIER, 1),
            (IE_SOURCE_TRANSPORT_PORT, 2),
            (IE_DESTINATION_TRANSPORT_PORT, 2),
            (IE_OCTET_DELTA_COUNT, 4),
            (IE_PACKET_DELTA_COUNT, 4),
            (IE_FLOW_DIRECTION, 1),
            (IE_TCP_CONTROL_BITS, 1),
        ]

        # Template record payload
        tmpl_record = struct.pack("!HH", template_id, len(fields))
        for ie_id, flen in fields:
            tmpl_record += struct.pack("!HH", ie_id, flen)

        # Set Header: Set ID = 2 (Template Set), Set Length = 4 + len(tmpl_record)
        set_length = 4 + len(tmpl_record)
        set_bytes = struct.pack("!HH", 2, set_length) + tmpl_record

        # Message Header: Version 10, Total Length, Export Time, Sequence Number, Obs Domain ID
        total_length = 16 + len(set_bytes)
        msg_header = struct.pack("!HHIII", 10, total_length, exp_time, sequence_number, observation_domain_id)

        return msg_header + set_bytes

    def build_data_packet(
        self,
        records: list[dict[str, Any]],
        observation_domain_id: int = 101,
        template_id: int = DEFAULT_TEMPLATE_ID,
        sequence_number: int = 1,
        export_time: int | None = None,
    ) -> bytes:
        """Construct an IPFIX Data Set message matching the standard template."""
        exp_time = export_time or int(time.time())
        data_payload = bytearray()

        for rec in records:
            src_ip_bytes = socket.inet_aton(rec.get("src_ip", "10.100.1.50"))
            dst_ip_bytes = socket.inet_aton(rec.get("dst_ip", "1.1.1.1"))
            proto = rec.get("protocol", 6)
            src_port = rec.get("src_port", 44321)
            dst_port = rec.get("dst_port", 443)
            bytes_count = rec.get("byte_count", 1500)
            packets_count = rec.get("packet_count", 10)
            direction = rec.get("direction", 1)  # 1 = Outbound
            tcp_flags = rec.get("tcp_flags", 24)

            record_bytes = struct.pack(
                "!4s4sBHHIIBB",
                src_ip_bytes,
                dst_ip_bytes,
                proto,
                src_port,
                dst_port,
                bytes_count,
                packets_count,
                direction,
                tcp_flags,
            )
            data_payload.extend(record_bytes)

        set_length = 4 + len(data_payload)
        set_bytes = struct.pack("!HH", template_id, set_length) + bytes(data_payload)

        total_length = 16 + len(set_bytes)
        msg_header = struct.pack("!HHIII", 10, total_length, exp_time, sequence_number, observation_domain_id)

        return msg_header + set_bytes

    def generate_normal_stream(
        self,
        count: int = 10,
        observation_domain_id: int = 101,
        start_seq: int = 1,
    ) -> list[SyntheticPacket]:
        """Generate an orderly stream starting with a template packet followed by data packets."""
        packets: list[SyntheticPacket] = []

        # First packet: Template definition
        tmpl_bytes = self.build_template_packet(
            observation_domain_id=observation_domain_id,
            sequence_number=start_seq,
        )
        packets.append(SyntheticPacket(raw_bytes=tmpl_bytes, sequence_number=start_seq))

        curr_seq = start_seq + 1
        common_destinations = ["1.1.1.1", "8.8.8.8", "142.250.190.46", "151.101.1.69"]
        protocols = [(6, 443), (6, 80), (17, 53), (17, 123), (6, 22)]

        for _ in range(count):
            proto, dst_p = self._rng.choice(protocols)
            records = [
                {
                    "src_ip": f"10.100.1.{self._rng.randint(2, 250)}",
                    "dst_ip": self._rng.choice(common_destinations),
                    "protocol": proto,
                    "src_port": self._rng.randint(49152, 65535),
                    "dst_port": dst_p,
                    "byte_count": self._rng.randint(128, 50000),
                    "packet_count": self._rng.randint(1, 40),
                    "direction": 1,
                    "tcp_flags": 16 if proto == 6 else 0,
                }
            ]
            data_bytes = self.build_data_packet(
                records=records,
                observation_domain_id=observation_domain_id,
                sequence_number=curr_seq,
            )
            packets.append(SyntheticPacket(raw_bytes=data_bytes, sequence_number=curr_seq))
            curr_seq += 1

        return packets

    def generate_fault_scenario(
        self,
        scenario: TrafficScenario,
        observation_domain_id: int = 101,
        count: int = 10,
    ) -> list[SyntheticPacket]:
        """Generate specific fault injection scenarios."""
        packets = self.generate_normal_stream(count=count, observation_domain_id=observation_domain_id)

        if scenario == TrafficScenario.SEQUENCE_GAP_FAULT:
            # Inject sequence jump: skip sequences 4 to 8 (gap of 5 packets)
            if len(packets) >= 6:
                for i in range(4, len(packets)):
                    packets[i].sequence_number += 5
                    # Rebuild packet with updated sequence number in header
                    header_prefix = struct.pack(
                        "!HHIII",
                        10,
                        len(packets[i].raw_bytes),
                        int(time.time()),
                        packets[i].sequence_number,
                        observation_domain_id,
                    )
                    packets[i].raw_bytes = header_prefix + packets[i].raw_bytes[16:]

        elif scenario == TrafficScenario.DUPLICATE_FLOW_FAULT:
            # Duplicate packet index 3
            if len(packets) >= 4:
                dup = SyntheticPacket(
                    raw_bytes=packets[3].raw_bytes,
                    sequence_number=packets[3].sequence_number,
                    is_duplicate=True,
                    scenario="duplicate",
                )
                packets.insert(4, dup)

        elif scenario == TrafficScenario.EXPORTER_RESTART_FAULT:
            # Exporter restarts: sequence number abruptly drops to 1
            if len(packets) >= 6:
                for i in range(5, len(packets)):
                    new_seq = i - 4
                    packets[i].sequence_number = new_seq
                    header_prefix = struct.pack(
                        "!HHIII",
                        10,
                        len(packets[i].raw_bytes),
                        int(time.time()),
                        new_seq,
                        observation_domain_id,
                    )
                    packets[i].raw_bytes = header_prefix + packets[i].raw_bytes[16:]

        elif scenario == TrafficScenario.CORRUPTED_PACKET_FAULT:
            # Truncate packet index 3 and inject bad length header at index 4
            if len(packets) >= 4:
                packets[2].raw_bytes = packets[2].raw_bytes[:8]  # Truncated
                packets[2].is_corrupted = True
            if len(packets) >= 5:
                # Header claims 5000 bytes, but buffer only has 40 bytes
                bad_len_header = struct.pack("!HHIII", 10, 5000, int(time.time()), 99, observation_domain_id)
                packets[3].raw_bytes = bad_len_header + b"\x00" * 24
                packets[3].is_corrupted = True

        elif scenario == TrafficScenario.UNKNOWN_TEMPLATE_FAULT:
            # Packet uses Template ID 999 which was never registered
            unknown_tmpl_bytes = self.build_data_packet(
                records=[{"src_ip": "10.100.1.10", "dst_ip": "8.8.8.8"}],
                observation_domain_id=observation_domain_id,
                template_id=999,
                sequence_number=99,
            )
            packets.append(SyntheticPacket(raw_bytes=unknown_tmpl_bytes, sequence_number=99, scenario="unknown_tmpl"))

        return packets
