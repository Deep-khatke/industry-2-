"""Exporter capability registry for common rural ISP router platforms."""

from typing import Any
from pydantic import BaseModel, Field


class ExporterCapabilityProfile(BaseModel):
    """Declared and tested capabilities for a network router/exporter family."""
    vendor: str
    device_family: str
    supported_protocols: list[str]  # e.g. ["IPFIX", "NetFlow_v9"]
    supported_fields: list[str]
    template_behavior: str
    sampling_behavior: str
    default_export_interval_sec: int
    clock_accuracy: str
    known_limitations: list[str]
    collector_requirements: list[str]
    compatible_feature_count: int = 14


class ExporterCapabilityRegistry:
    """Registry of known ISP exporter profiles and capabilities."""

    PROFILES: dict[str, ExporterCapabilityProfile] = {
        "cisco_asr": ExporterCapabilityProfile(
            vendor="Cisco",
            device_family="ASR 1000 / ISR 4000",
            supported_protocols=["IPFIX", "NetFlow_v9"],
            supported_fields=[
                "sourceIPv4Address",
                "destinationIPv4Address",
                "sourceTransportPort",
                "destinationTransportPort",
                "protocolIdentifier",
                "octetDeltaCount",
                "packetDeltaCount",
                "tcpControlBits",
                "flowStartMilliseconds",
                "flowEndMilliseconds",
                "ipClassOfService",
                "bgpSourceAsNumber",
                "bgpDestinationAsNumber",
            ],
            template_behavior="Periodic template export every 60s or 1000 packets (RFC 7011 compliant)",
            sampling_behavior="Hardware ASIC 1-in-N deterministic or 1-in-1 un-sampled",
            default_export_interval_sec=15,
            clock_accuracy="PTP / NTP synchronized (< 1ms drift)",
            known_limitations=[
                "High CPU utilization if un-sampled 1-in-1 active on 10Gbps+ interfaces; recommend 1-in-10 sampling under high load."
            ],
            collector_requirements=["UDP port 2055", "Dynamic template cache"],
            compatible_feature_count=14,
        ),
        "juniper_mx": ExporterCapabilityProfile(
            vendor="Juniper",
            device_family="MX Series (MX204, MX480, MX960)",
            supported_protocols=["IPFIX", "NetFlow_v9"],
            supported_fields=[
                "sourceIPv4Address",
                "destinationIPv4Address",
                "sourceTransportPort",
                "destinationTransportPort",
                "protocolIdentifier",
                "octetDeltaCount",
                "packetDeltaCount",
                "tcpControlBits",
                "flowStartMilliseconds",
                "flowEndMilliseconds",
                "ipClassOfService",
            ],
            template_behavior="Inline J-Flow export with dynamic template negotiation",
            sampling_behavior="Inline Packet Mirroring / Hardware sampling",
            default_export_interval_sec=15,
            clock_accuracy="NTP synchronized (< 5ms drift)",
            known_limitations=[
                "Flow record timestamps may be rounded to nearest 10ms depending on JunOS release."
            ],
            collector_requirements=["UDP port 2055", "Inline flow table buffering"],
            compatible_feature_count=14,
        ),
        "mikrotik_ccr": ExporterCapabilityProfile(
            vendor="MikroTik",
            device_family="CCR2004 / CCR2116 RouterOS v7",
            supported_protocols=["NetFlow_v9", "IPFIX"],
            supported_fields=[
                "sourceIPv4Address",
                "destinationIPv4Address",
                "sourceTransportPort",
                "destinationTransportPort",
                "protocolIdentifier",
                "octetDeltaCount",
                "packetDeltaCount",
                "tcpControlBits",
                "flowStartMilliseconds",
                "flowEndMilliseconds",
            ],
            template_behavior="Traffic Flow v9/IPFIX periodic template announcements",
            sampling_behavior="Software sampling (1:1 to 1:1000)",
            default_export_interval_sec=30,
            clock_accuracy="SNTP synchronized",
            known_limitations=[
                "Microsecond timestamps not supported; milliseconds used exclusively.",
                "Export queue can drop flows under > 80% CPU load without hardware offload.",
            ],
            collector_requirements=["UDP port 2055", "Sequence gap reconciliation buffer"],
            compatible_feature_count=14,
        ),
        "linux_softflowd": ExporterCapabilityProfile(
            vendor="Linux",
            device_family="softflowd / ipt_NETFLOW (Linux Gateway)",
            supported_protocols=["IPFIX", "NetFlow_v9"],
            supported_fields=[
                "sourceIPv4Address",
                "destinationIPv4Address",
                "sourceTransportPort",
                "destinationTransportPort",
                "protocolIdentifier",
                "octetDeltaCount",
                "packetDeltaCount",
                "tcpControlBits",
                "flowStartMilliseconds",
                "flowEndMilliseconds",
            ],
            template_behavior="Standard RFC 7011 IPFIX templates",
            sampling_behavior="Software pcap / netfilter sampling",
            default_export_interval_sec=10,
            clock_accuracy="Kernel system clock (chrony / ntpd)",
            known_limitations=[
                "High kernel context switching on raw socket capture under > 1Gbps traffic.",
            ],
            collector_requirements=["UDP port 2055"],
            compatible_feature_count=14,
        ),
        "huawei_ne": ExporterCapabilityProfile(
            vendor="Huawei",
            device_family="NetEngine 8000 Series (VRP)",
            supported_protocols=["IPFIX", "NetFlow_v9"],
            supported_fields=[
                "sourceIPv4Address",
                "destinationIPv4Address",
                "sourceTransportPort",
                "destinationTransportPort",
                "protocolIdentifier",
                "octetDeltaCount",
                "packetDeltaCount",
                "tcpControlBits",
                "flowStartMilliseconds",
                "flowEndMilliseconds",
            ],
            template_behavior="NetStream v9/IPFIX flexible flow templates",
            sampling_behavior="Hardware-based packet sampling",
            default_export_interval_sec=20,
            clock_accuracy="NTP synchronized",
            known_limitations=[
                "Requires flexible flow configuration on sub-interfaces for bi-directional flow counting.",
            ],
            collector_requirements=["UDP port 2055"],
            compatible_feature_count=14,
        ),
        "vyos_router": ExporterCapabilityProfile(
            vendor="VyOS",
            device_family="VyOS 1.4 / 1.5 SAGITTA",
            supported_protocols=["IPFIX", "NetFlow_v9"],
            supported_fields=[
                "sourceIPv4Address",
                "destinationIPv4Address",
                "sourceTransportPort",
                "destinationTransportPort",
                "protocolIdentifier",
                "octetDeltaCount",
                "packetDeltaCount",
                "tcpControlBits",
                "flowStartMilliseconds",
                "flowEndMilliseconds",
            ],
            template_behavior="FastNetMon / pmacct IPFIX export templates",
            sampling_behavior="Software sampling",
            default_export_interval_sec=15,
            clock_accuracy="System clock / NTP",
            known_limitations=[
                "Flow aggregation interval defaults to 60s if not explicitly configured in vyos CLI.",
            ],
            collector_requirements=["UDP port 2055"],
            compatible_feature_count=14,
        ),
        "pfsense_firewall": ExporterCapabilityProfile(
            vendor="pfSense",
            device_family="pfSense Plus / CE (FreeBSD softflowd)",
            supported_protocols=["NetFlow_v9"],
            supported_fields=[
                "sourceIPv4Address",
                "destinationIPv4Address",
                "sourceTransportPort",
                "destinationTransportPort",
                "protocolIdentifier",
                "octetDeltaCount",
                "packetDeltaCount",
                "tcpControlBits",
                "flowStartMilliseconds",
                "flowEndMilliseconds",
            ],
            template_behavior="Fixed NetFlow v9 template",
            sampling_behavior="FreeBSD kernel bpf / softflowd",
            default_export_interval_sec=30,
            clock_accuracy="NTP synchronized",
            known_limitations=[
                "Only NetFlow v9 supported in standard package; IPFIX requires custom package.",
                "Export sequence numbers may wrap during rapid state purges.",
            ],
            collector_requirements=["UDP port 2055", "Wrap-around sequence handling"],
            compatible_feature_count=14,
        ),
    }

    @classmethod
    def get_profile(cls, key: str) -> ExporterCapabilityProfile | None:
        return cls.PROFILES.get(key.lower())

    @classmethod
    def find_by_vendor(cls, vendor: str) -> list[ExporterCapabilityProfile]:
        v_clean = vendor.strip().lower()
        return [p for p in cls.PROFILES.values() if v_clean in p.vendor.lower()]

    @classmethod
    def list_all(cls) -> dict[str, ExporterCapabilityProfile]:
        return dict(cls.PROFILES)
