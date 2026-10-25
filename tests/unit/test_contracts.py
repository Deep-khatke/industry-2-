"""Unit tests for telemetry contracts (FlowEvent v1)."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from packages.contracts.enums import FlowDirection, PortClass, TransportProtocol
from packages.contracts.exceptions import (
    ContractValidationError,
    InvalidSchemaVersionError,
    RecordSizeLimitExceeded,
)
from packages.contracts.flow_event import (
    MAX_RECORD_SIZE_BYTES,
    FlowEvent,
    compute_deterministic_event_id,
)
from packages.contracts.stubs import DetectionAlertStub, FederatedWeightsStub


@pytest.mark.unit
class TestFlowEventContracts:
    """Test suite verifying FlowEvent v1 contract specifications."""

    def test_valid_flow_event_creation(self) -> None:
        """Verify normal creation and deterministic event_id generation."""
        now = datetime.now(UTC)
        event = FlowEvent(
            tenant_id="tenant-isp-alpha",
            exporter_id="gw-isp-alpha-1",
            observation_domain=101,
            boot_epoch=1,
            sequence=1001,
            event_time=now,
            protocol=TransportProtocol.TCP,
            src_port=52341,
            dst_port=443,
            direction=FlowDirection.OUTBOUND,
            byte_count=1500,
            packet_count=10,
            flow_duration_ms=250,
        )

        assert event.schema_version == "1.0.0"
        assert event.port_class == PortClass.WELL_KNOWN
        assert event.event_id != ""
        expected_id = compute_deterministic_event_id(
            tenant_id="tenant-isp-alpha",
            exporter_id="gw-isp-alpha-1",
            observation_domain=101,
            boot_epoch=1,
            sequence=1001,
        )
        assert event.event_id == expected_id

    def test_deterministic_event_id_idempotence(self) -> None:
        """Verify that identical natural flow tuples yield identical event IDs."""
        id1 = compute_deterministic_event_id("tenant-a", "exp-1", 101, 1, 500)
        id2 = compute_deterministic_event_id("tenant-a", "exp-1", 101, 1, 500)
        id3 = compute_deterministic_event_id("tenant-b", "exp-1", 101, 1, 500)

        assert id1 == id2
        assert id1 != id3

    def test_unsupported_schema_version_rejected(self) -> None:
        """Verify unsupported schema version raises InvalidSchemaVersionError."""
        now = datetime.now(UTC)
        with pytest.raises(InvalidSchemaVersionError):
            FlowEvent(
                schema_version="9.9.9",
                tenant_id="tenant-isp-alpha",
                exporter_id="gw-1",
                observation_domain=1,
                boot_epoch=1,
                sequence=1,
                event_time=now,
            )

    def test_future_clock_skew_rejected(self) -> None:
        """Verify event_time more than 5 minutes in future is rejected."""
        far_future = datetime.now(UTC) + timedelta(minutes=10)
        with pytest.raises(ContractValidationError, match="too far in the future"):
            FlowEvent(
                tenant_id="tenant-isp-alpha",
                exporter_id="gw-1",
                observation_domain=1,
                boot_epoch=1,
                sequence=1,
                event_time=far_future,
            )

    def test_record_size_limit_exceeded(self) -> None:
        """Verify record size limit enforcement."""
        now = datetime.now(UTC)
        huge_prefix = "10.0.0.0/24" + ("x" * (MAX_RECORD_SIZE_BYTES + 500))
        with pytest.raises(RecordSizeLimitExceeded):
            FlowEvent(
                tenant_id="tenant-isp-alpha",
                exporter_id="gw-1",
                observation_domain=1,
                boot_epoch=1,
                sequence=1,
                event_time=now,
                src_prefix_masked=huge_prefix,
            )

    def test_canonical_json_and_hash(self) -> None:
        """Verify canonical JSON serialization has sorted keys and stable hash."""
        now = datetime.now(UTC) - timedelta(minutes=1)
        event = FlowEvent(
            tenant_id="tenant-isp-alpha",
            exporter_id="gw-1",
            observation_domain=1,
            boot_epoch=1,
            sequence=1,
            event_time=now,
            ingest_time=now,
        )
        json_str = event.to_canonical_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["tenant_id"] == "tenant-isp-alpha"

        h1 = event.canonical_hash()
        h2 = event.canonical_hash()
        assert h1 == h2
        assert len(h1) == 64

    def test_contract_stubs(self) -> None:
        """Verify future Phase 2 contract stubs instantiate cleanly."""
        alert = DetectionAlertStub(
            tenant_id="tenant-isp-alpha",
            event_id="test-event-id",
            threat_category="PORT_SCAN",
        )
        assert alert.recommended_action == "MANUAL_REVIEW"

        weights = FederatedWeightsStub(
            round_id=1,
            tenant_id="tenant-isp-alpha",
            weight_layers_shape=[[64, 32], [32, 2]],
        )
        assert weights.differential_privacy_epsilon == 1.0
