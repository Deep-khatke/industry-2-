# Federated Cyber Shield (FCS) v1.2 — Service Level Objectives (SLOs) & Performance

## 1. Production SLO Targets vs. Measured Evidence

Performance benchmarks were executed using `tools/performance/benchmark_suite.py` against production-sized synthetic flow batches and candidate models on standard CPU compute:

| Metric Identifier | Service Level Objective (Target) | Measured Performance | Margin / Status |
|---|---|---|---|
| **SLO-HMD-p50** | Hierarchical ML p50 latency < **25.0 ms** | **9.68 ms – 11.69 ms** | **PASS** (+53% headroom) |
| **SLO-HMD-p95** | Hierarchical ML p95 latency < **50.0 ms** | **14.21 ms – 18.45 ms** | **PASS** (+63% headroom) |
| **SLO-HMD-p99** | Hierarchical ML p99 latency < **100.0 ms** | **22.80 ms – 29.10 ms** | **PASS** (+70% headroom) |
| **SLO-PIPE-TP** | Pipeline Replay Throughput > **50.0 flows/sec** | **74.75 flows/sec** | **PASS** (+49% headroom) |
| **SLO-PIPE-p95** | Pipeline End-to-End Scoring p95 < **1000.0 ms** | **585.50 ms** | **PASS** (+41% headroom) |
| **SLO-REC-RTO** | Disaster Recovery Time Objective < **60.0 sec** | **0.032 s – 0.050 s** | **PASS** (Sub-second recovery) |
| **SLO-REC-RPO** | Recovery Point Objective = **0 dropped WAL tx** | **0 dropped tx** | **PASS** (Zero corruption) |

---

## 2. Resource Utilization & Zero-Cost Constraints

- **CPU Footprint**: LightGBM tree evaluation and Isolation Forest anomaly scoring require less than 1.5 CPU cores at maximum pipeline load.
- **Memory Footprint**: Working set memory remains bounded under 350 MB RAM for the combined API, feature window buffer, and model registry.
- **Disk I/O**: SQLite WAL mode minimizes fsync write amplification during continuous flow aggregation.
