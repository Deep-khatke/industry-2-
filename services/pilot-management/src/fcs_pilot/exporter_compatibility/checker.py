"""Exporter compatibility checker and telemetry validation routines."""

import logging
from datetime import UTC, datetime
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger("fcs_pilot.exporter_checker")


class ExporterCheckResult(BaseModel):
    """Outcome of an exporter compatibility and telemetry health check."""
    exporter_id: str
    vendor: str
    protocol: str
    template_valid: bool
    fields_detected: list[str]
    missing_required_fields: list[str]
    sequence_gap_detected: bool = False
    sequence_gap_count: int = 0
    clock_drift_seconds: float = 0.0
    sampling_rate: int = 1
    sampling_corrected: bool = False
    status: str  # "COMPATIBLE", "DEGRADED", "INCOMPATIBLE"
    recommendations: list[str] = Field(default_factory=list)


class ExporterCompatibilityChecker:
    """Validates exporter telemetry records and template parity."""

    REQUIRED_FIELDS = [
        "sourceIPv4Address",
        "destinationIPv4Address",
        "sourceTransportPort",
        "destinationTransportPort",
        "protocolIdentifier",
        "octetDeltaCount",
        "packetDeltaCount",
        "flowStartMilliseconds",
        "flowEndMilliseconds",
    ]

    def __init__(self) -> None:
        self._sequence_trackers: dict[str, int] = {}

    def check_record_batch(
        self,
        exporter_id: str,
        vendor: str,
        protocol: str,
        records: list[dict[str, Any]],
        declared_sampling_rate: int = 1,
        sequence_number: int | None = None,
    ) -> ExporterCheckResult:
        """
        Validate a batch of exporter records against schema and sequence requirements.
        """
        if not records:
            return ExporterCheckResult(
                exporter_id=exporter_id,
                vendor=vendor,
                protocol=protocol,
                template_valid=False,
                fields_detected=[],
                missing_required_fields=self.REQUIRED_FIELDS,
                status="INCOMPATIBLE",
                recommendations=["No flow records received in batch."],
            )

        # Inspect first record for detected fields
        sample = records[0]
        detected_fields = list(sample.keys())
        missing = [f for f in self.REQUIRED_FIELDS if f not in detected_fields]

        template_valid = len(missing) == 0

        # Sequence gap checking
        sequence_gap_detected = False
        gap_count = 0
        if sequence_number is not None:
            prev_seq = self._sequence_trackers.get(exporter_id)
            if prev_seq is not None:
                expected_seq = prev_seq + 1
                if sequence_number > expected_seq:
                    sequence_gap_detected = True
                    gap_count = sequence_number - expected_seq
                    logger.warning(
                        f"Sequence gap detected for {exporter_id}: expected {expected_seq}, got {sequence_number} ({gap_count} missed)."
                    )
                elif sequence_number < prev_seq:
                    logger.info(f"Exporter {exporter_id} sequence reset/reboot detected (was {prev_seq}, now {sequence_number}).")
            self._sequence_trackers[exporter_id] = sequence_number

        # Clock drift check
        now_ms = datetime.now(UTC).timestamp() * 1000.0
        sample_time_ms = sample.get("flowEndMilliseconds", now_ms)
        clock_drift = abs(now_ms - float(sample_time_ms)) / 1000.0

        recs: list[str] = []
        if missing:
            recs.append(f"Exporter does not furnish required fields: {missing}. Update exporter template.")
        if clock_drift > 10.0:
            recs.append(f"Observed clock drift of {clock_drift:.1f}s exceeds recommended threshold of 5.0s. Verify NTP sync.")
        if declared_sampling_rate > 1:
            recs.append(f"Exporter configured for 1:{declared_sampling_rate} packet sampling. Scaling correction enabled.")

        if not template_valid:
            status = "INCOMPATIBLE"
        elif clock_drift > 60.0 or sequence_gap_detected:
            status = "DEGRADED"
        else:
            status = "COMPATIBLE"

        return ExporterCheckResult(
            exporter_id=exporter_id,
            vendor=vendor,
            protocol=protocol,
            template_valid=template_valid,
            fields_detected=detected_fields,
            missing_required_fields=missing,
            sequence_gap_detected=sequence_gap_detected,
            sequence_gap_count=gap_count,
            clock_drift_seconds=round(clock_drift, 3),
            sampling_rate=declared_sampling_rate,
            sampling_corrected=(declared_sampling_rate > 1),
            status=status,
            recommendations=recs,
        )
