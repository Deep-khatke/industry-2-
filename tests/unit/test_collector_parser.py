"""Unit tests for IPFIX binary protocol parser and normalizer."""

import struct
import time

import pytest

from packages.contracts.enums import FlowDirection, PortClass, TransportProtocol
from services.telemetry_collector.normalizer import TelemetryNormalizer
from services.telemetry_collector.protocol import (
    CorruptedMessageError,
    IPFIXParser,
    ProtocolError,
    TemplateDefinition,
)
from tools.synthetic_exporter.generator import SyntheticTrafficGenerator


@pytest.mark.unit
class TestCollectorProtocolParser:
    """Test suite verifying binary parser correctness and boundary safety."""

    def test_parse_valid_ipfix_header(self) -> None:
        """Verify RFC 7011 IPFIX 16-byte message header decoding."""
        raw_header = struct.pack("!HHIII", 10, 48, 1700000000, 105, 201)
        header = IPFIXParser.parse_header(raw_header + (b"\x00" * 32))

        assert header.version == 10
        assert header.length == 48
        assert header.export_time == 1700000000
        assert header.sequence_number == 105
        assert header.observation_domain_id == 201

    def test_parse_valid_netflow9_header(self) -> None:
        """Verify RFC 3954 NetFlow v9 20-byte message header decoding."""
        raw_header = struct.pack("!HHIIII", 9, 2, 50000, 1700000000, 1001, 301)
        header = IPFIXParser.parse_header(raw_header)

        assert header.version == 9
        assert header.export_time == 1700000000
        assert header.sequence_number == 1001
        assert header.observation_domain_id == 301

    def test_unsupported_protocol_version_rejected(self) -> None:
        """Verify unsupported version (e.g., NetFlow v5) raises ProtocolError."""
        bad_header = struct.pack("!HHIII", 5, 48, 1700000000, 105, 201)
        with pytest.raises(ProtocolError, match="Unsupported telemetry protocol version"):
            IPFIXParser.parse_header(bad_header)

    def test_truncated_header_rejected(self) -> None:
        """Verify truncated buffer raises CorruptedMessageError."""
        short_bytes = b"\x00\x0a\x00\x10"
        with pytest.raises(CorruptedMessageError):
            IPFIXParser.parse_header(short_bytes)

    def test_header_declared_length_exceeds_buffer(self) -> None:
        """Verify header declaring length greater than buffer is rejected."""
        # Header claims length is 1000 bytes, but buffer is only 16 bytes
        bad_header = struct.pack("!HHIII", 10, 1000, 1700000000, 1, 101)
        with pytest.raises(CorruptedMessageError, match="declares length 1000 bytes, but received only 16"):
            IPFIXParser.parse_header(bad_header)

    def test_end_to_end_template_and_data_set_parsing(self) -> None:
        """Verify parsing synthetic template and data sets produced by generator."""
        generator = SyntheticTrafficGenerator(seed=123)

        # 1. Generate template packet
        tmpl_bytes = generator.build_template_packet(observation_domain_id=101, template_id=256)
        header = IPFIXParser.parse_header(tmpl_bytes)
        template_store: dict[int, TemplateDefinition] = {}

        parsed_tmpl_pkt = IPFIXParser.parse_sets(tmpl_bytes, header, template_store)
        assert len(parsed_tmpl_pkt.new_templates) == 1
        assert 256 in template_store
        assert template_store[256].template_id == 256
        assert len(template_store[256].fields) == 9

        # 2. Generate data packet matching template 256
        records = [
            {
                "src_ip": "10.100.1.25",
                "dst_ip": "1.1.1.1",
                "protocol": 6,
                "src_port": 54321,
                "dst_port": 443,
                "byte_count": 2048,
                "packet_count": 12,
                "direction": 1,
                "tcp_flags": 16,
            }
        ]
        data_bytes = generator.build_data_packet(
            records=records,
            observation_domain_id=101,
            template_id=256,
            sequence_number=2,
        )
        data_header = IPFIXParser.parse_header(data_bytes)
        parsed_data_pkt = IPFIXParser.parse_sets(data_bytes, data_header, template_store)

        assert len(parsed_data_pkt.data_sets) == 1
        tid, raw_records = parsed_data_pkt.data_sets[0]
        assert tid == 256
        assert len(raw_records) == 1
        rec = raw_records[0]
        assert rec[8] == "10.100.1.25"
        assert rec[12] == "1.1.1.1"
        assert rec[4] == 6
        assert rec[7] == 54321
        assert rec[11] == 443
        assert rec[1] == 2048
        assert rec[2] == 12

    def test_normalizer_subscriber_ip_masking(self) -> None:
        """Verify TelemetryNormalizer preserves privacy by masking subscriber IPs to /24."""
        raw_fields = {
            8: "10.100.1.145",   # source subscriber IP
            12: "142.250.190.46", # destination IP
            4: 6,                 # TCP
            7: 50123,
            11: 443,
            1: 4096,
            2: 8,
            61: 1,                # Outbound
        }

        event = TelemetryNormalizer.normalize_record(
            raw_fields=raw_fields,
            trusted_tenant_id="tenant-isp-alpha",
            exporter_id="gw-isp-alpha-1",
            observation_domain=101,
            boot_epoch=1,
            sequence=50,
            export_time_seconds=int(time.time()),
        )

        assert event.src_prefix_masked == "10.100.1.0/24"
        assert event.dst_prefix_masked == "142.250.190.0/24"
        assert event.protocol == TransportProtocol.TCP
        assert event.port_class == PortClass.WELL_KNOWN
        assert event.direction == FlowDirection.OUTBOUND
        assert event.byte_count == 4096
