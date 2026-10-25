# Federated Cyber Shield (FCS) v1.2 — Telemetry Operations Runbook

## 1. Operational Principles
- **Manual Response by Default**: Automatic network filtering or BGP blackholing remains disabled. All remediation recommendations require human ISP operator validation.
- **Coverage Visibility**: Absence of flow records from an exporter or tenant edge MUST NOT be interpreted as an absence of security threats. Missing telemetry must trigger degraded coverage investigations.

---

## 2. Standard Operating Procedures (SOP)

### SOP-01: Investigating Parser Errors & Malformed Packets
**Symptom**: `events_rejected` or `packets_corrupted` counters incrementing in metrics dashboard.
1. Check collector structured logs:
   ```bash
   grep -i "Failed to decode telemetry header" /var/log/fcs/collector.log
   ```
2. Identify source IP address of transmitting appliance.
3. Verify if router MTU or UDP fragmentation is causing packet truncation (< 16 bytes).
4. Verify router IPFIX export version (must be 10 for IPFIX or 9 for NetFlow v9; NetFlow v5 is rejected).

### SOP-02: Handling Sequence Gaps & Packet Loss
**Symptom**: `sequence_gaps` alarm fires; tenant coverage transitions to `DEGRADED`.
1. Check gap size in metrics: `SequenceGaps` sum over 60 seconds.
2. Determine if packet loss is occurring across backhaul transit or collector NIC buffers.
3. If exporter rebooted, check `boot_epoch` increment or sequence reset logs.
4. Notify rural ISP network engineering of potential WAN congestion or dropped UDP datagrams.

### SOP-03: Investigating Unregistered Templates
**Symptom**: `invalid_templates` metric increments.
1. Inspect logs for `Data record arrived for unregistered template ID <TID>`.
2. Determine whether exporter has transmitted a Template Set message recently.
3. IPFIX RFC 7011 requires periodic retransmission of Template Records over UDP. Adjust router export template timeout to 600 seconds or less.

### SOP-04: Stream Adapter Failures (Sink Backpressure)
**Symptom**: `stream_write_failures` metric increments.
1. **Memory Sink**: Check if `max_capacity` (100,000) was exceeded. Drain or flush events.
2. **SQLite Sink**: Check if disk space is full or SQLite database is locked by concurrent transaction. WAL mode is enabled by default to allow concurrent readers.
3. **AWS Kinesis (Future)**: Check `WriteProvisionedThroughputExceeded` on Kinesis shard metrics. Scale shards if incoming telemetry exceeds 1 MB/s or 1,000 records/s per shard.

### SOP-05: Coverage Degradation & Outage Response
**Symptom**: `CoverageStatus` switches to `DEGRADED`, `UNKNOWN`, or `DEAD`.
1. Run coverage assessment:
   ```python
   from packages.observability.coverage import CoverageTracker
   # Review get_tenant_coverage(tenant_id)
   ```
2. If `CoverageStatus.DEAD` (no telemetry for > 120s):
   - Treat edge network as unmonitored.
   - Do NOT mark alerts as cleared or threats as zero.
   - Contact ISP NOC to verify edge router telemetry daemon status.
