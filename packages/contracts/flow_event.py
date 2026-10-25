"""FlowEvent v1 data contract for Federated Cyber Shield."""

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from .enums import FlowDirection, PortClass, TransportProtocol
from .exceptions import ContractValidationError, InvalidSchemaVersionError, RecordSizeLimitExceeded

SUPPORTED_SCHEMA_VERSIONS = ["1.0.0"]
MAX_RECORD_SIZE_BYTES = 4096  # Bounded memory limit per serialized record
MAX_FUTURE_CLOCK_SKEW_SECONDS = 300  # 5 minutes maximum forward drift


def compute_deterministic_event_id(
    tenant_id: str,
    exporter_id: str,
    observation_domain: int,
    boot_epoch: int,
    sequence: int,
) -> str:
    """
    Generate a deterministic UUID-5 event ID based on the natural flow tuple.
    Guarantees idempotency and duplicate detection across replayed streams.
    """
    canonical_key = f"{tenant_id}:{exporter_id}:{observation_domain}:{boot_epoch}:{sequence}"
    namespace = uuid.UUID("a7e1f420-1b77-4fa5-9833-88402db2e2bc")
    return str(uuid.uuid5(namespace, canonical_key))


class FlowEvent(BaseModel):
    """
    Normalized, privacy-preserving IPFIX/NetFlow v9 telemetry event.
    Conforms strictly to FCS v1.2 Phase 1 data contract specifications.
    """

    schema_version: str = Field(default="1.0.0", description="Contract schema version")
    event_id: str = Field(
        default="",
        description="Deterministic idempotent event identifier (UUID v5 format)",
    )
    tenant_id: str = Field(..., min_length=3, max_length=64, description="Trusted tenant identifier")
    exporter_id: str = Field(..., min_length=2, max_length=64, description="Originating exporter identifier")
    observation_domain: int = Field(..., ge=0, le=4294967295, description="IPFIX Observation Domain ID")
    boot_epoch: int = Field(
        ...,
        ge=0,
        description="Exporter boot epoch / sysUptime anchor to disambiguate sequence resets",
    )
    sequence: int = Field(..., ge=0, le=4294967295, description="Flow sequence or message index")
    event_time: datetime = Field(..., description="Flow observation time at the exporter in UTC")
    ingest_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Collector ingestion arrival time in UTC",
    )
    sample_rate: int = Field(default=1, ge=1, description="1-in-N sampling rate")

    # Normalized flow telemetry metadata (Subscriber IP masked for privacy)
    protocol: TransportProtocol = Field(default=TransportProtocol.OTHER)
    port_class: PortClass = Field(default=PortClass.UNKNOWN)
    src_port: int | None = Field(default=None, ge=0, le=65535)
    dst_port: int | None = Field(default=None, ge=0, le=65535)
    direction: FlowDirection = Field(default=FlowDirection.UNKNOWN)
    byte_count: int = Field(default=0, ge=0)
    packet_count: int = Field(default=0, ge=0)
    flow_duration_ms: int = Field(default=0, ge=0)
    tcp_flags: int | None = Field(default=None, ge=0, le=255)
    src_prefix_masked: str | None = Field(
        default=None,
        description="Privacy-preserved /24 or /48 network prefix, never raw subscriber host IP",
    )
    dst_prefix_masked: str | None = Field(
        default=None,
        description="Privacy-preserved destination network prefix",
    )

    def __init__(self, **data: Any) -> None:
        try:
            super().__init__(**data)
        except ValidationError as e:
            for err in e.errors():
                ctx = err.get("ctx", {})
                orig = ctx.get("error")
                if isinstance(orig, ContractValidationError):
                    raise orig from e
            raise

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        if v not in SUPPORTED_SCHEMA_VERSIONS:
            raise InvalidSchemaVersionError(v, SUPPORTED_SCHEMA_VERSIONS)
        return v

    @model_validator(mode="before")
    @classmethod
    def populate_defaults_and_validate(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Ensure UTC timezone awareness on timestamps
        for ts_field in ("event_time", "ingest_time"):
            val = data.get(ts_field)
            if isinstance(val, str):
                try:
                    dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=UTC)
                    data[ts_field] = dt
                except ValueError as e:
                    raise ContractValidationError(f"Invalid timestamp format for '{ts_field}': {val}") from e
            elif isinstance(val, datetime) and val.tzinfo is None:
                data[ts_field] = val.replace(tzinfo=UTC)

        # Auto-compute deterministic event_id if not explicitly provided
        if not data.get("event_id"):
            tenant_id = data.get("tenant_id", "")
            exporter_id = data.get("exporter_id", "")
            observation_domain = data.get("observation_domain", 0)
            boot_epoch = data.get("boot_epoch", 0)
            sequence = data.get("sequence", 0)
            data["event_id"] = compute_deterministic_event_id(
                tenant_id=str(tenant_id),
                exporter_id=str(exporter_id),
                observation_domain=int(observation_domain),
                boot_epoch=int(boot_epoch),
                sequence=int(sequence),
            )

        # Automatically classify port_class if not provided or UNKNOWN
        if data.get("port_class") in (None, PortClass.UNKNOWN, "UNKNOWN"):
            dst_port = data.get("dst_port")
            if dst_port is not None:
                data["port_class"] = PortClass.classify(int(dst_port))

        return data

    @model_validator(mode="after")
    def validate_timestamps_and_size(self) -> "FlowEvent":
        now_utc = datetime.now(UTC)
        max_allowed_future = now_utc + timedelta(seconds=MAX_FUTURE_CLOCK_SKEW_SECONDS)
        if self.event_time > max_allowed_future:
            raise ContractValidationError(
                f"event_time '{self.event_time.isoformat()}' is too far in the future "
                f"(max allowed forward skew is {MAX_FUTURE_CLOCK_SKEW_SECONDS}s)."
            )

        # Enforce serialized memory size limit
        serialized = self.to_canonical_json()
        size_bytes = len(serialized.encode("utf-8"))
        if size_bytes > MAX_RECORD_SIZE_BYTES:
            raise RecordSizeLimitExceeded(size_bytes, MAX_RECORD_SIZE_BYTES)

        return self

    def to_canonical_json(self) -> str:
        """Stable, deterministic JSON serialization with sorted keys."""
        dump_dict = self.model_dump(mode="json")
        return json.dumps(dump_dict, sort_keys=True)

    def canonical_hash(self) -> str:
        """SHA-256 hash of the canonical JSON representation."""
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_json(cls, json_str: str) -> "FlowEvent":
        """Parse and validate a FlowEvent from a JSON string."""
        raw_size = len(json_str.encode("utf-8"))
        if raw_size > MAX_RECORD_SIZE_BYTES:
            raise RecordSizeLimitExceeded(raw_size, MAX_RECORD_SIZE_BYTES)
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ContractValidationError(f"Malformed JSON payload: {e}") from e
        return cls(**parsed)
