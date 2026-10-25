"""AWS Kinesis Stream Sink Adapter (Deferred / Offline Mode for Zero-Cost Phase 1)."""

from typing import Any

from packages.contracts.flow_event import FlowEvent

from ..base import SinkError, SinkWriteError, StreamSink


class SinkDisabledError(SinkError):
    """Raised when an operation is attempted on a stream sink disabled by the Zero-Cost Policy."""


class KinesisStreamSink(StreamSink):
    """
    AWS Kinesis data stream adapter for future production deployment.

    CRITICAL ZERO-COST COMPLIANCE:
    - Disabled by default (`enabled=False`).
    - Does NOT require AWS credentials or active internet connection to import or instantiate.
    - Offline unit tests verify payload formatting and partitioning logic using injected mock clients.
    - Real network requests to AWS are strictly prevented during Phase 1.
    """

    def __init__(
        self,
        stream_name: str = "fcs-telemetry-stream-dev",
        region_name: str = "us-east-1",
        enabled: bool = False,
        client: Any = None,  # Injected mock or stub client
    ) -> None:
        self.stream_name = stream_name
        self.region_name = region_name
        self.enabled = enabled
        self._client = client

    def write(self, event: FlowEvent) -> None:
        if not self.enabled:
            raise SinkDisabledError(
                "AWS Kinesis sink is DISABLED under the FCS Zero-Cost Policy. "
                "No live AWS infrastructure is provisioned during Phase 1."
            )

        if self._client is None:
            raise SinkWriteError("Kinesis client is not configured (mock client required).")

        # Partition key is explicitly scoped by tenant_id to preserve tenant data isolation
        # across stream shards while preventing cross-tenant partition collisions
        partition_key = f"{event.tenant_id}#{event.exporter_id}"
        payload = event.to_canonical_json().encode("utf-8")

        try:
            self._client.put_record(
                StreamName=self.stream_name,
                Data=payload,
                PartitionKey=partition_key,
            )
        except Exception as e:
            raise SinkWriteError(f"Failed to put record to Kinesis: {e}") from e

    def write_batch(self, events: list[FlowEvent]) -> int:
        if not self.enabled:
            raise SinkDisabledError("AWS Kinesis sink is DISABLED under Zero-Cost Policy.")

        if not events:
            return 0

        if self._client is None:
            raise SinkWriteError("Kinesis client is not configured (mock client required).")

        records = [
            {
                "Data": e.to_canonical_json().encode("utf-8"),
                "PartitionKey": f"{e.tenant_id}#{e.exporter_id}",
            }
            for e in events
        ]

        try:
            resp = self._client.put_records(
                StreamName=self.stream_name,
                Records=records,
            )
            failed_count = int(resp.get("FailedRecordCount", 0))
            return int(len(events) - failed_count)
        except Exception as e:
            raise SinkWriteError(f"Failed to put batch to Kinesis: {e}") from e

    def flush(self) -> None:
        """Kinesis client handles request dispatch immediately."""

    def close(self) -> None:
        """Close client if applicable."""
