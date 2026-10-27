"""Feature specification contracts and parity definitions for FCS-UDIP."""

import hashlib
import json
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class FeatureAvailabilityStatus(StrEnum):
    """Production availability status of benchmark features relative to collector capabilities."""

    DIRECTLY_AVAILABLE = "DIRECTLY_AVAILABLE"
    DERIVABLE_WITH_VERIFIED_TRANSFORM = "DERIVABLE_WITH_VERIFIED_TRANSFORM"
    REQUIRES_ADDITIONAL_EXPORT_FIELDS = "REQUIRES_ADDITIONAL_EXPORT_FIELDS"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED_OR_AMBIGUOUS = "UNSUPPORTED_OR_AMBIGUOUS"


class FeatureDefinition(BaseModel):
    """Formal schema contract for a single feature in the canonical benchmark or deployable view."""

    name: str = Field(..., description="Canonical feature name (uppercase snake_case)")
    data_type: str = Field(..., description="Target data type (e.g., int64, float32, string)")
    semantic_meaning: str = Field(..., description="Human and machine-readable semantic description")
    unit: str = Field(default="dimensionless", description="Measurement unit (e.g., bytes, packets, ms, bps)")
    valid_range: tuple[float | None, float | None] | None = Field(
        default=None,
        description="Permissible [min, max] range where applicable",
    )
    nullable: bool = Field(default=False, description="Whether NULL/None is permitted")
    missing_value_interpretation: str = Field(
        default="REJECT",
        description="Policy when missing: 'IMPUTE_ZERO', 'IMPUTE_MEDIAN', 'REJECT'",
    )
    original_dataset_field: str = Field(..., description="Field name in raw source dataset")
    transformation_function: str = Field(
        default="identity",
        description="Identifier of transformation applied during harmonization",
    )
    version: str = Field(default="1.0.0", description="Feature schema version")
    production_availability: FeatureAvailabilityStatus = Field(
        default=FeatureAvailabilityStatus.UNAVAILABLE,
        description="Availability status against Phase 1 FlowEvent v1 telemetry collector",
    )
    flow_event_mapping: str | None = Field(
        default=None,
        description="Corresponding field name in FlowEvent v1 if available or derivable",
    )


class FeatureSpec(BaseModel):
    """
    Complete versioned specification of a feature view (Research or Deployable).
    Provides schema digest computation for tamper-evident data pipelines.
    """

    spec_id: str = Field(..., description="Unique specification identifier (e.g., fcs-netflow-v2-research)")
    version: str = Field(default="1.0.0", description="Specification version")
    description: str = Field(..., description="Description of the feature specification")
    is_deployable_subset: bool = Field(
        default=False,
        description="True if this spec contains strictly deployable features matching live telemetry",
    )
    features: list[FeatureDefinition] = Field(..., description="Ordered list of feature definitions")

    def feature_names(self) -> list[str]:
        """Return ordered list of feature names."""
        return [f.name for f in self.features]

    def compute_schema_digest(self) -> str:
        """
        Compute deterministic SHA-256 digest of the ordered feature schema.
        Ensures any alteration of feature names, types, or order invalidates cached artifacts.
        """
        canonical_representation = [
            {
                "name": f.name,
                "data_type": f.data_type,
                "unit": f.unit,
                "nullable": f.nullable,
                "production_availability": f.production_availability.value,
            }
            for f in self.features
        ]
        serialized = json.dumps(canonical_representation, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get_feature(self, name: str) -> FeatureDefinition | None:
        """Find feature definition by name."""
        for f in self.features:
            if f.name == name:
                return f
        return None


# =====================================================================
# Canonical 43 NetFlow v2 Extended Features Registry
# Authoritative source: Marius Sarhan et al. (Univ. of Queensland, 2021)
# =====================================================================

CANONICAL_NETFLOW_V2_43_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "IPV4_SRC_ADDR",
        "data_type": "string",
        "semantic_meaning": "IPv4 source address (masked or dropped in ML predictors to prevent testbed overfitting)",
        "unit": "ip_address",
        "nullable": False,
        "missing_value_interpretation": "REJECT",
        "original_dataset_field": "IPV4_SRC_ADDR",
        "production_availability": FeatureAvailabilityStatus.DERIVABLE_WITH_VERIFIED_TRANSFORM,
        "flow_event_mapping": "src_prefix_masked",
    },
    {
        "name": "IPV4_DST_ADDR",
        "data_type": "string",
        "semantic_meaning": "IPv4 destination address (masked or dropped in ML predictors)",
        "unit": "ip_address",
        "nullable": False,
        "missing_value_interpretation": "REJECT",
        "original_dataset_field": "IPV4_DST_ADDR",
        "production_availability": FeatureAvailabilityStatus.DERIVABLE_WITH_VERIFIED_TRANSFORM,
        "flow_event_mapping": "dst_prefix_masked",
    },
    {
        "name": "L4_SRC_PORT",
        "data_type": "int64",
        "semantic_meaning": "Layer 4 transport source port number",
        "unit": "port_number",
        "valid_range": (0, 65535),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "L4_SRC_PORT",
        "production_availability": FeatureAvailabilityStatus.DIRECTLY_AVAILABLE,
        "flow_event_mapping": "src_port",
    },
    {
        "name": "L4_DST_PORT",
        "data_type": "int64",
        "semantic_meaning": "Layer 4 transport destination port number",
        "unit": "port_number",
        "valid_range": (0, 65535),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "L4_DST_PORT",
        "production_availability": FeatureAvailabilityStatus.DIRECTLY_AVAILABLE,
        "flow_event_mapping": "dst_port",
    },
    {
        "name": "PROTOCOL",
        "data_type": "int64",
        "semantic_meaning": "IP protocol byte identifier (6=TCP, 17=UDP, 1=ICMP)",
        "unit": "protocol_id",
        "valid_range": (0, 255),
        "nullable": False,
        "missing_value_interpretation": "REJECT",
        "original_dataset_field": "PROTOCOL",
        "production_availability": FeatureAvailabilityStatus.DIRECTLY_AVAILABLE,
        "flow_event_mapping": "protocol",
    },
    {
        "name": "L7_PROTO",
        "data_type": "float32",
        "semantic_meaning": "Layer 7 application protocol identifier derived from nProbe deep packet inspection",
        "unit": "proto_id",
        "valid_range": (0, 1000),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "L7_PROTO",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "IN_BYTES",
        "data_type": "int64",
        "semantic_meaning": "Incoming number of bytes in the flow (client to server)",
        "unit": "bytes",
        "valid_range": (0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "IN_BYTES",
        "production_availability": FeatureAvailabilityStatus.DIRECTLY_AVAILABLE,
        "flow_event_mapping": "byte_count",
    },
    {
        "name": "OUT_BYTES",
        "data_type": "int64",
        "semantic_meaning": "Outgoing number of bytes in the flow (server to client)",
        "unit": "bytes",
        "valid_range": (0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "OUT_BYTES",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "IN_PKTS",
        "data_type": "int64",
        "semantic_meaning": "Incoming number of packets in the flow",
        "unit": "packets",
        "valid_range": (0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "IN_PKTS",
        "production_availability": FeatureAvailabilityStatus.DIRECTLY_AVAILABLE,
        "flow_event_mapping": "packet_count",
    },
    {
        "name": "OUT_PKTS",
        "data_type": "int64",
        "semantic_meaning": "Outgoing number of packets in the flow",
        "unit": "packets",
        "valid_range": (0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "OUT_PKTS",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "FLOW_DURATION_MILLISECONDS",
        "data_type": "int64",
        "semantic_meaning": "Total duration of the flow in milliseconds",
        "unit": "milliseconds",
        "valid_range": (0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "FLOW_DURATION_MILLISECONDS",
        "production_availability": FeatureAvailabilityStatus.DIRECTLY_AVAILABLE,
        "flow_event_mapping": "flow_duration_ms",
    },
    {
        "name": "TCP_FLAGS",
        "data_type": "int64",
        "semantic_meaning": "Cumulative bitwise OR of all TCP flags observed in flow",
        "unit": "flags_mask",
        "valid_range": (0, 255),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "TCP_FLAGS",
        "production_availability": FeatureAvailabilityStatus.DIRECTLY_AVAILABLE,
        "flow_event_mapping": "tcp_flags",
    },
    {
        "name": "CLIENT_TCP_FLAGS",
        "data_type": "int64",
        "semantic_meaning": "Cumulative TCP flags sent by client (initiator)",
        "unit": "flags_mask",
        "valid_range": (0, 255),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "CLIENT_TCP_FLAGS",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "SERVER_TCP_FLAGS",
        "data_type": "int64",
        "semantic_meaning": "Cumulative TCP flags sent by server (responder)",
        "unit": "flags_mask",
        "valid_range": (0, 255),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "SERVER_TCP_FLAGS",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "DURATION_IN",
        "data_type": "int64",
        "semantic_meaning": "Client to server stream duration in milliseconds",
        "unit": "milliseconds",
        "valid_range": (0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "DURATION_IN",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "DURATION_OUT",
        "data_type": "int64",
        "semantic_meaning": "Server to client stream duration in milliseconds",
        "unit": "milliseconds",
        "valid_range": (0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "DURATION_OUT",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "MIN_TTL",
        "data_type": "int64",
        "semantic_meaning": "Minimum Time-To-Live value observed in flow",
        "unit": "hops",
        "valid_range": (0, 255),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "MIN_TTL",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "MAX_TTL",
        "data_type": "int64",
        "semantic_meaning": "Maximum Time-To-Live value observed in flow",
        "unit": "hops",
        "valid_range": (0, 255),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "MAX_TTL",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "LONGEST_FLOW_PKT",
        "data_type": "int64",
        "semantic_meaning": "Length in bytes of the longest packet in the flow",
        "unit": "bytes",
        "valid_range": (0, 65535),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "LONGEST_FLOW_PKT",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "SHORTEST_FLOW_PKT",
        "data_type": "int64",
        "semantic_meaning": "Length in bytes of the shortest packet in the flow",
        "unit": "bytes",
        "valid_range": (0, 65535),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "SHORTEST_FLOW_PKT",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "MIN_IP_PKT_LEN",
        "data_type": "int64",
        "semantic_meaning": "Length in bytes of the smallest IP packet observed",
        "unit": "bytes",
        "valid_range": (0, 65535),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "MIN_IP_PKT_LEN",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "MAX_IP_PKT_LEN",
        "data_type": "int64",
        "semantic_meaning": "Length in bytes of the largest IP packet observed",
        "unit": "bytes",
        "valid_range": (0, 65535),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "MAX_IP_PKT_LEN",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "SRC_TO_DST_SECOND_BYTES",
        "data_type": "float32",
        "semantic_meaning": "Average bytes per second transmitted from source to destination",
        "unit": "bytes_per_sec",
        "valid_range": (0.0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "SRC_TO_DST_SECOND_BYTES",
        "production_availability": FeatureAvailabilityStatus.DERIVABLE_WITH_VERIFIED_TRANSFORM,
        "flow_event_mapping": "byte_count / (flow_duration_ms / 1000)",
    },
    {
        "name": "DST_TO_SRC_SECOND_BYTES",
        "data_type": "float32",
        "semantic_meaning": "Average bytes per second transmitted from destination to source",
        "unit": "bytes_per_sec",
        "valid_range": (0.0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "DST_TO_SRC_SECOND_BYTES",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "RETRANSMITTED_IN_BYTES",
        "data_type": "int64",
        "semantic_meaning": "Number of retransmitted TCP bytes in incoming flow",
        "unit": "bytes",
        "valid_range": (0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "RETRANSMITTED_IN_BYTES",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "RETRANSMITTED_IN_PKTS",
        "data_type": "int64",
        "semantic_meaning": "Number of retransmitted TCP packets in incoming flow",
        "unit": "packets",
        "valid_range": (0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "RETRANSMITTED_IN_PKTS",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "RETRANSMITTED_OUT_BYTES",
        "data_type": "int64",
        "semantic_meaning": "Number of retransmitted TCP bytes in outgoing flow",
        "unit": "bytes",
        "valid_range": (0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "RETRANSMITTED_OUT_BYTES",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "RETRANSMITTED_OUT_PKTS",
        "data_type": "int64",
        "semantic_meaning": "Number of retransmitted TCP packets in outgoing flow",
        "unit": "packets",
        "valid_range": (0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "RETRANSMITTED_OUT_PKTS",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "SRC_TO_DST_AVG_THROUGHPUT",
        "data_type": "float32",
        "semantic_meaning": "Source to destination average throughput in bits per second",
        "unit": "bps",
        "valid_range": (0.0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "SRC_TO_DST_AVG_THROUGHPUT",
        "production_availability": FeatureAvailabilityStatus.DERIVABLE_WITH_VERIFIED_TRANSFORM,
        "flow_event_mapping": "(byte_count * 8) / (flow_duration_ms / 1000)",
    },
    {
        "name": "DST_TO_SRC_AVG_THROUGHPUT",
        "data_type": "float32",
        "semantic_meaning": "Destination to source average throughput in bits per second",
        "unit": "bps",
        "valid_range": (0.0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "DST_TO_SRC_AVG_THROUGHPUT",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "NUM_PKTS_UP_TO_128_BYTES",
        "data_type": "int64",
        "semantic_meaning": "Number of packets in flow with size <= 128 bytes",
        "unit": "packets",
        "valid_range": (0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "NUM_PKTS_UP_TO_128_BYTES",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "NUM_PKTS_128_TO_256_BYTES",
        "data_type": "int64",
        "semantic_meaning": "Number of packets in flow with size > 128 and <= 256 bytes",
        "unit": "packets",
        "valid_range": (0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "NUM_PKTS_128_TO_256_BYTES",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "NUM_PKTS_256_TO_512_BYTES",
        "data_type": "int64",
        "semantic_meaning": "Number of packets in flow with size > 256 and <= 512 bytes",
        "unit": "packets",
        "valid_range": (0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "NUM_PKTS_256_TO_512_BYTES",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "NUM_PKTS_512_TO_1024_BYTES",
        "data_type": "int64",
        "semantic_meaning": "Number of packets in flow with size > 512 and <= 1024 bytes",
        "unit": "packets",
        "valid_range": (0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "NUM_PKTS_512_TO_1024_BYTES",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "NUM_PKTS_1024_TO_1514_BYTES",
        "data_type": "int64",
        "semantic_meaning": "Number of packets in flow with size > 1024 and <= 1514 bytes",
        "unit": "packets",
        "valid_range": (0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "NUM_PKTS_1024_TO_1514_BYTES",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "TCP_WIN_MAX_IN",
        "data_type": "int64",
        "semantic_meaning": "Maximum TCP window advertisement observed from source to destination",
        "unit": "window_size",
        "valid_range": (0, 65535),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "TCP_WIN_MAX_IN",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "TCP_WIN_MAX_OUT",
        "data_type": "int64",
        "semantic_meaning": "Maximum TCP window advertisement observed from destination to source",
        "unit": "window_size",
        "valid_range": (0, 65535),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "TCP_WIN_MAX_OUT",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "ICMP_TYPE",
        "data_type": "int64",
        "semantic_meaning": "ICMP Type * 256 + ICMP code",
        "unit": "icmp_encoded",
        "valid_range": (0, 65535),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "ICMP_TYPE",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "ICMP_IPV4_TYPE",
        "data_type": "int64",
        "semantic_meaning": "ICMP Type numeric code (0=Echo Reply, 8=Echo Request, 3=Dest Unreach)",
        "unit": "icmp_type",
        "valid_range": (0, 255),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "ICMP_IPV4_TYPE",
        "production_availability": FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS,
        "flow_event_mapping": None,
    },
    {
        "name": "DNS_QUERY_ID",
        "data_type": "int64",
        "semantic_meaning": "DNS transaction ID from payload",
        "unit": "query_id",
        "valid_range": (0, 65535),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "DNS_QUERY_ID",
        "production_availability": FeatureAvailabilityStatus.UNAVAILABLE,
        "flow_event_mapping": None,
    },
    {
        "name": "DNS_QUERY_TYPE",
        "data_type": "int64",
        "semantic_meaning": "DNS resource record type requested (1=A, 28=AAAA, etc.)",
        "unit": "query_type",
        "valid_range": (0, 65535),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "DNS_QUERY_TYPE",
        "production_availability": FeatureAvailabilityStatus.UNAVAILABLE,
        "flow_event_mapping": None,
    },
    {
        "name": "DNS_TTL_ANSWER",
        "data_type": "int64",
        "semantic_meaning": "DNS TTL value of first resource record answer",
        "unit": "seconds",
        "valid_range": (0, None),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "DNS_TTL_ANSWER",
        "production_availability": FeatureAvailabilityStatus.UNAVAILABLE,
        "flow_event_mapping": None,
    },
    {
        "name": "FTP_COMMAND_RET_CODE",
        "data_type": "float32",
        "semantic_meaning": "FTP response status return code (e.g. 220, 230, 530)",
        "unit": "status_code",
        "valid_range": (0.0, 999.0),
        "nullable": False,
        "missing_value_interpretation": "IMPUTE_ZERO",
        "original_dataset_field": "FTP_COMMAND_RET_CODE",
        "production_availability": FeatureAvailabilityStatus.UNAVAILABLE,
        "flow_event_mapping": None,
    },
]


def get_research_feature_spec() -> FeatureSpec:
    """Return the complete canonical 43-feature research specification."""
    features = [FeatureDefinition(**item) for item in CANONICAL_NETFLOW_V2_43_DEFINITIONS]
    return FeatureSpec(
        spec_id="fcs-netflow-v2-43-research",
        version="1.2.0",
        description="Canonical 43 extended NetFlow v2 benchmark feature schema (Sarhan et al. 2021)",
        is_deployable_subset=False,
        features=features,
    )


def get_deployable_feature_spec() -> FeatureSpec:
    """
    Return the deployable feature subset that can be strictly supplied or derived
    from the Phase 1 FlowEvent v1 telemetry collector without unsupported payload fields.
    """
    research_spec = get_research_feature_spec()
    deployable_features = [
        f
        for f in research_spec.features
        if f.production_availability
        in (
            FeatureAvailabilityStatus.DIRECTLY_AVAILABLE,
            FeatureAvailabilityStatus.DERIVABLE_WITH_VERIFIED_TRANSFORM,
        )
    ]
    return FeatureSpec(
        spec_id="fcs-deployable-flowevent-v1",
        version="1.2.0",
        description="Production-deployable telemetry features available from Phase 1 FlowEvent v1",
        is_deployable_subset=True,
        features=deployable_features,
    )
