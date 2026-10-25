"""Enumerations for normalized network telemetry metadata."""

from enum import StrEnum


class TransportProtocol(StrEnum):
    """Normalized IP transport protocol."""

    TCP = "TCP"
    UDP = "UDP"
    ICMP = "ICMP"
    ICMPV6 = "ICMPv6"
    GRE = "GRE"
    ESP = "ESP"
    OTHER = "OTHER"

    @classmethod
    def from_iana_number(cls, proto_num: int) -> "TransportProtocol":
        """Map IANA protocol numbers to enum."""
        mapping = {
            1: cls.ICMP,
            6: cls.TCP,
            17: cls.UDP,
            47: cls.GRE,
            50: cls.ESP,
            58: cls.ICMPV6,
        }
        return mapping.get(proto_num, cls.OTHER)


class PortClass(StrEnum):
    """Categorization of transport layer ports per RFC 6335."""

    WELL_KNOWN = "WELL_KNOWN"          # 0 - 1023 (System/Well-Known)
    REGISTERED = "REGISTERED"          # 1024 - 49151 (User/Registered)
    DYNAMIC_EPHEMERAL = "DYNAMIC"      # 49152 - 65535 (Dynamic/Private/Ephemeral)
    UNKNOWN = "UNKNOWN"

    @classmethod
    def classify(cls, port: int | None) -> "PortClass":
        """Determine port class from integer port number."""
        if port is None or port < 0 or port > 65535:
            return cls.UNKNOWN
        if port <= 1023:
            return cls.WELL_KNOWN
        if port <= 49151:
            return cls.REGISTERED
        return cls.DYNAMIC_EPHEMERAL


class FlowDirection(StrEnum):
    """Flow directionality relative to the rural ISP access edge."""

    INBOUND = "INBOUND"        # Ingress from Internet towards subscriber
    OUTBOUND = "OUTBOUND"      # Egress from subscriber towards Internet
    INTERNAL = "INTERNAL"      # Intra-ISP lateral traffic
    UNKNOWN = "UNKNOWN"
