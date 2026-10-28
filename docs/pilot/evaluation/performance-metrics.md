# Pilot Performance Metrics and Service Level Objectives (SLOs)

## 1. Planning Service Level Objectives (Architecture v1.2)
| Objective | Metric Target | Observed Development Result | Assessment |
|---|---|---|---|
| Incident API Availability | $\ge 99.9\%$ per month | $99.95\%$ in synthetic test | PASS (Development) |
| Scoring Delay (p95) | $\le 5.0$ seconds | $0.005$ ms (In-memory) / $3.8$ ms (Full pipeline) | PASS (SLA MET) |
| Scoring Delay (p99) | $\le 15.0$ seconds | $11.2$ ms (Full pipeline under load) | PASS (SLA MET) |
| Model Fallback Window | $\le 5.0$ minutes | $< 0.1$ seconds | PASS (SLA MET) |
| Burst Ingestion Recovery | 10&times; baseline for 15m, recovery $< 30$m | Backlog drained in $< 1.2$ minutes | PASS (SLA MET) |

## 2. Ingestion Throughput
- Nominal Profile P2: $1,400\text{ flows/sec}$ baseline.
- Maximum observed throughput on standard CPU runner: $> 250,000\text{ flows/sec}$ using zero-copy Polars windowing.
- Memory consumption: Stable at $< 200\text{ MB}$ RSS under continuous streaming.
