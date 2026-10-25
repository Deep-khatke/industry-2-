# Architecture Decision Record (ADR) 0002: Bounded IPFIX/NetFlow v9 Subset and StreamSink Abstraction

## Status
Accepted

## Context
Rural ISPs operate diverse edge routing equipment exporting telemetry via IPFIX (RFC 7011) and NetFlow v9 (RFC 3954). The FCS collector must process high-volume flow records reliably without denial-of-service vulnerability, memory exhaustion, or vendor lock-in.

## Decision
1. **Standards-Compliant Bounded Subset**:
   - Rather than attempting to implement every obscure vendor enterprise information element in Phase 1, FCS implements a standards-compliant subset of RFC 7011 / RFC 3954.
   - Supported IANA elements: `octetDeltaCount` (1), `packetDeltaCount` (2), `protocolIdentifier` (4), `tcpControlBits` (6), `sourceTransportPort` (7), `sourceIPv4Address` (8), `destinationTransportPort` (11), `destinationIPv4Address` (12), `flowDirection` (61), `flowStartMilliseconds` (152), and `flowEndMilliseconds` (153).
   - Unknown templates and unsupported element sets are gracefully caught and recorded in observability metrics without interrupting service.

2. **Strict Memory Bounds**:
   - Bounded packet buffer size: 65,507 bytes (maximum physical UDP packet).
   - Bounded serialized event size: 4,096 bytes per normalized record.
   - Bounded histogram sample limits: 1,000 samples per metric window.

3. **Pluggable StreamSink Protocol**:
   - Consumers write to a `StreamSink` protocol supporting `write(event)`, `write_batch(events)`, `flush()`, and `close()`.
   - Idempotency is enforced using deterministic UUID v5 event IDs calculated from `(tenant_id, exporter_id, observation_domain, boot_epoch, sequence)`.

## Consequences
- Fast parsing, bounded memory safety, robust duplicate handling, and smooth migration from local testing (SQLite) to production (AWS Kinesis).
