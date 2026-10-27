# Federated Cyber Shield (FCS) v1.2 — Telemetry Monitoring Guide
## ISP Exporter Health, Stream Freshness, Ingestion Delay & Data Completeness

**Status:** OPERATIONAL & TESTED (Gate G02: PASS)  
**Supported Telemetry:** NetFlow v5/v9, IPFIX, Synthetic Replay  

---

## 1. Exporter Health & Freshness States

In an operational Security Operations Center (SOC), telemetry health is as vital as threat detection. A silent exporter must never be mistaken for a benign network. FCS continuously evaluates exporter freshness:

```text
[Current Time] - [Last Exporter Timestamp]
                    │
   ┌────────────────┼────────────────┐
   ▼                ▼                ▼
< 60s            60s – 300s        > 300s
HEALTHY          DEGRADED          STALE / UNKNOWN
(Normal stream)  (Lagging stream)  (Warning Banner in SOC)
```

### Health Status Classification

| Status | Lag Threshold | System Behavior | SOC UI Display |
| :--- | :--- | :--- | :--- |
| `HEALTHY` | $\text{delay} < 60\text{s}$ | Continuous real-time feature windowing | Green pulse badge, normal ingestion |
| `DEGRADED` | $60\text{s} \le \text{delay} \le 300\text{s}$ | Ingests into late-event buffer | Amber warning badge |
| `STALE` | $\text{delay} > 300\text{s}$ | Window completeness marked partial | Red alert badge: "Telemetry Stale" |
| `UNKNOWN` | No records recorded | System registers exporter as unverified | Gray badge: "No Telemetry" |

> [!IMPORTANT]
> **Zero Telemetry Is Never Zero Threats:** If an exporter ceases transmitting data, the system explicitly refuses to label the tenant as "Secure". The dashboard displays an alert notifying operators that monitoring coverage is degraded.

---

## 2. Telemetry Processing Pipeline

```text
Raw NetFlow / IPFIX Packet
            │
            ▼
[Collector / Replay Parser]
            │
            ├─► Validate supported protocol version (NetFlow v5/v9 / IPFIX)
            ├─► Validate source exporter identity against tenant inventory
            ├─► Validate flow timestamp monotonicity
            ├─► Check for sequence number gaps
            │
            ▼
[FlowEvent v1 Normalizer]
            │
            ├─► Compute flow duration (last_switched - first_switched)
            ├─► Extract TCP flags, protocol, byte/packet volumes
            │
            ▼
[Durable Stream / SQLite Storage]
            │
            ▼
[WindowEngine (30s event-time)]
```

---

## 3. Monitoring APIs

- `GET /v1/coverage`: Returns real-time health, total flow count, received records, processing lag, and completeness metrics for every exporter bound to the authorized tenant.
- `GET /v1/overview`: Aggregated telemetry metrics including total monitored flows, flows processed in the last 15 minutes, exporter summary, and detection throughput.
