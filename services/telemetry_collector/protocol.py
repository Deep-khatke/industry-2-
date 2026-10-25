"""IPFIX (RFC 7011) and NetFlow v9 (RFC 3954) binary protocol parser."""

import socket
import struct
from dataclasses import dataclass
from typing import Any

IPFIX_VERSION = 10
NETFLOW_V9_VERSION = 9

IPFIX_TEMPLATE_SET_ID = 2
IPFIX_OPTIONS_TEMPLATE_SET_ID = 3
NETFLOW_V9_TEMPLATE_SET_ID = 0
NETFLOW_V9_OPTIONS_TEMPLATE_SET_ID = 1

# Supported IANA IPFIX Information Element Identifiers
IE_OCTET_DELTA_COUNT = 1
IE_PACKET_DELTA_COUNT = 2
IE_PROTOCOL_IDENTIFIER = 4
IE_TCP_CONTROL_BITS = 6
IE_SOURCE_TRANSPORT_PORT = 7
IE_SOURCE_IPV4_ADDRESS = 8
IE_DESTINATION_TRANSPORT_PORT = 11
IE_DESTINATION_IPV4_ADDRESS = 12
IE_FLOW_DIRECTION = 61
IE_FLOW_START_MILLISECONDS = 152
IE_FLOW_END_MILLISECONDS = 153


class ProtocolError(Exception):
    """Raised when an IPFIX or NetFlow packet violates protocol format or constraints."""


class CorruptedMessageError(ProtocolError):
    """Raised when message header or length is truncated or inconsistent."""


class UnsupportedTemplateError(ProtocolError):
    """Raised when a data record references an unknown or unregistered template ID."""

    def __init__(self, template_id: int) -> None:
        super().__init__(f"Data record references unregistered template ID {template_id}.")
        self.template_id = template_id


@dataclass(frozen=True)
class FieldSpecifier:
    """Specification of an individual field in an IPFIX template."""

    element_id: int
    length: int
    is_enterprise: bool = False
    enterprise_number: int | None = None


@dataclass
class TemplateDefinition:
    """Template structure defining fields and record sizes for data sets."""

    template_id: int
    fields: list[FieldSpecifier]

    @property
    def total_record_length(self) -> int:
        return sum(f.length for f in self.fields)


@dataclass
class MessageHeader:
    """Unified representation of IPFIX / NetFlow v9 packet headers."""

    version: int
    length: int
    export_time: int
    sequence_number: int
    observation_domain_id: int


@dataclass
class ParsedPacket:
    """Decoded protocol packet containing header, templates, and raw data records."""

    header: MessageHeader
    new_templates: list[TemplateDefinition]
    # List of (template_id, list of raw field dictionaries)
    data_sets: list[tuple[int, list[dict[int, Any]]]]


class IPFIXParser:
    """
    Standards-compliant binary decoder for IPFIX and NetFlow v9 telemetry.
    Operates strictly within bounded memory buffers to prevent denial-of-service.
    """

    MAX_MESSAGE_BYTES = 65535
    MIN_IPFIX_HEADER_BYTES = 16
    MIN_NETFLOW9_HEADER_BYTES = 20

    @classmethod
    def parse_header(cls, buffer: bytes) -> MessageHeader:
        """Parse and validate message header."""
        if len(buffer) < 4:
            raise CorruptedMessageError(f"Buffer too short for protocol identification ({len(buffer)} bytes).")

        version = struct.unpack("!H", buffer[0:2])[0]

        if version == IPFIX_VERSION:
            if len(buffer) < cls.MIN_IPFIX_HEADER_BYTES:
                raise CorruptedMessageError(
                    f"IPFIX message truncated: {len(buffer)} bytes, expected >= {cls.MIN_IPFIX_HEADER_BYTES}."
                )
            version, length, export_time, sequence_number, obs_domain = struct.unpack(
                "!HHIII", buffer[0:cls.MIN_IPFIX_HEADER_BYTES]
            )
            if length > len(buffer):
                raise CorruptedMessageError(
                    f"IPFIX header declares length {length} bytes, but received only {len(buffer)} bytes."
                )
            if length < cls.MIN_IPFIX_HEADER_BYTES:
                raise CorruptedMessageError(f"Invalid IPFIX message length {length} (< header size).")
            return MessageHeader(
                version=version,
                length=length,
                export_time=export_time,
                sequence_number=sequence_number,
                observation_domain_id=obs_domain,
            )

        elif version == NETFLOW_V9_VERSION:
            if len(buffer) < cls.MIN_NETFLOW9_HEADER_BYTES:
                raise CorruptedMessageError(
                    f"NetFlow v9 message truncated: {len(buffer)} bytes, expected >= {cls.MIN_NETFLOW9_HEADER_BYTES}."
                )
            version, count, sys_uptime, unix_secs, seq_num, source_id = struct.unpack(
                "!HHIIII", buffer[0:cls.MIN_NETFLOW9_HEADER_BYTES]
            )
            return MessageHeader(
                version=version,
                length=len(buffer),  # NetFlow v9 uses UDP payload length
                export_time=unix_secs,
                sequence_number=seq_num,
                observation_domain_id=source_id,
            )

        else:
            raise ProtocolError(f"Unsupported telemetry protocol version: {version}. Expected 10 (IPFIX) or 9 (NetFlow v9).")

    @classmethod
    def parse_sets(
        cls,
        buffer: bytes,
        header: MessageHeader,
        template_lookup: dict[int, TemplateDefinition],
    ) -> ParsedPacket:
        """
        Parse Sets / FlowSets contained in the message payload.
        Applies known templates to decode data records.
        """
        offset = cls.MIN_IPFIX_HEADER_BYTES if header.version == IPFIX_VERSION else cls.MIN_NETFLOW9_HEADER_BYTES
        max_offset = min(header.length, len(buffer))

        new_templates: list[TemplateDefinition] = []
        data_sets: list[tuple[int, list[dict[int, Any]]]] = []

        is_ipfix = header.version == IPFIX_VERSION
        template_set_id = IPFIX_TEMPLATE_SET_ID if is_ipfix else NETFLOW_V9_TEMPLATE_SET_ID
        options_set_id = IPFIX_OPTIONS_TEMPLATE_SET_ID if is_ipfix else NETFLOW_V9_OPTIONS_TEMPLATE_SET_ID

        while offset + 4 <= max_offset:
            set_id, set_length = struct.unpack("!HH", buffer[offset : offset + 4])
            if set_length < 4:
                raise CorruptedMessageError(f"Invalid Set length {set_length} (< 4 bytes) at offset {offset}.")
            if offset + set_length > max_offset:
                raise CorruptedMessageError(
                    f"Set {set_id} length {set_length} exceeds message bounds (remaining: {max_offset - offset})."
                )

            set_payload = buffer[offset + 4 : offset + set_length]

            if set_id == template_set_id:
                # Template Set
                templates = cls._parse_template_set(set_payload)
                new_templates.extend(templates)
                for t in templates:
                    template_lookup[t.template_id] = t
            elif set_id == options_set_id:
                # Options template set - safely ignored or parsed in subset mode
                pass
            elif set_id >= 256:
                # Data Set matching template ID
                target_template = template_lookup.get(set_id)
                if target_template is None:
                    # Unknown template: per requirements, record unknown and handle safely
                    data_sets.append((set_id, []))
                else:
                    records = cls._parse_data_records(set_payload, target_template)
                    data_sets.append((set_id, records))

            offset += set_length

        return ParsedPacket(
            header=header,
            new_templates=new_templates,
            data_sets=data_sets,
        )

    @classmethod
    def _parse_template_set(cls, payload: bytes) -> list[TemplateDefinition]:
        """Decode template definitions from a Template Set payload."""
        templates: list[TemplateDefinition] = []
        offset = 0
        total_len = len(payload)

        while offset + 4 <= total_len:
            template_id, field_count = struct.unpack("!HH", payload[offset : offset + 4])
            offset += 4
            fields: list[FieldSpecifier] = []

            for _ in range(field_count):
                if offset + 4 > total_len:
                    raise CorruptedMessageError("Truncated field specifier in template record.")
                element_id, field_len = struct.unpack("!HH", payload[offset : offset + 4])
                offset += 4

                is_enterprise = bool(element_id & 0x8000)
                element_id = element_id & 0x7FFF
                ent_num = None
                if is_enterprise:
                    if offset + 4 > total_len:
                        raise CorruptedMessageError("Truncated enterprise number in field specifier.")
                    ent_num = struct.unpack("!I", payload[offset : offset + 4])[0]
                    offset += 4

                fields.append(
                    FieldSpecifier(
                        element_id=element_id,
                        length=field_len,
                        is_enterprise=is_enterprise,
                        enterprise_number=ent_num,
                    )
                )

            templates.append(TemplateDefinition(template_id=template_id, fields=fields))

        return templates

    @classmethod
    def _parse_data_records(
        cls,
        payload: bytes,
        template: TemplateDefinition,
    ) -> list[dict[int, Any]]:
        """Decode data records matching the specified template definition."""
        record_len = template.total_record_length
        if record_len == 0:
            return []

        records: list[dict[int, Any]] = []
        offset = 0
        total_len = len(payload)

        while offset + record_len <= total_len:
            rec_dict: dict[int, Any] = {}
            rec_offset = offset
            for f in template.fields:
                raw_val = payload[rec_offset : rec_offset + f.length]
                rec_dict[f.element_id] = cls._decode_field_value(f.element_id, raw_val)
                rec_offset += f.length
            records.append(rec_dict)
            offset += record_len

        return records

    @staticmethod
    def _decode_field_value(element_id: int, raw_bytes: bytes) -> Any:
        """Decode raw binary field into typed Python representation."""
        length = len(raw_bytes)
        if element_id in (IE_OCTET_DELTA_COUNT, IE_PACKET_DELTA_COUNT, IE_FLOW_START_MILLISECONDS, IE_FLOW_END_MILLISECONDS):
            if length == 1:
                return struct.unpack("!B", raw_bytes)[0]
            if length == 2:
                return struct.unpack("!H", raw_bytes)[0]
            if length == 4:
                return struct.unpack("!I", raw_bytes)[0]
            if length == 8:
                return struct.unpack("!Q", raw_bytes)[0]
            return int.from_bytes(raw_bytes, byteorder="big")

        if element_id in (IE_SOURCE_TRANSPORT_PORT, IE_DESTINATION_TRANSPORT_PORT):
            if length == 2:
                return struct.unpack("!H", raw_bytes)[0]
            return int.from_bytes(raw_bytes, byteorder="big")

        if element_id == IE_PROTOCOL_IDENTIFIER:
            return raw_bytes[0] if length > 0 else 0

        if element_id == IE_TCP_CONTROL_BITS:
            return raw_bytes[-1] if length > 0 else 0

        if element_id == IE_FLOW_DIRECTION:
            return raw_bytes[0] if length > 0 else 0

        if element_id in (IE_SOURCE_IPV4_ADDRESS, IE_DESTINATION_IPV4_ADDRESS):
            if length == 4:
                return socket.inet_ntoa(raw_bytes)
            return "0.0.0.0"

        # Default fallback: return unsigned integer or raw bytes
        if length <= 8:
            return int.from_bytes(raw_bytes, byteorder="big")
        return raw_bytes
