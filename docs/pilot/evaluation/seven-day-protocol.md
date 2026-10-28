# Seven-Day Shadow Monitoring Protocol

## 1. Requirement & Rationale
In compliance with Architecture v1.2 Release Gate G07 and Phase 9 Specification Section 11, FCS must operate in read-only Shadow Mode for **at least seven representative consecutive calendar days** on ISP traffic prior to any automated response qualification.

## 2. Daily Required Observations
For each of the 7 monitoring days, the system records:
1. Total flows received, valid flows, and rejected flows.
2. Sequence gaps and exporter clock drift.
3. Exporter coverage percentage ($\ge 99.0\%$).
4. Model-scored windows vs unscored windows.
5. Candidate incidents generated vs analyst-confirmed true positives.
6. Grouped false alerts per day.
7. Total analyst review time (minutes).
8. Latency metrics: $p95 \le 5.0\text{s}, p99 \le 15.0\text{s}$.

## 3. Strict Separation of Real vs Synthetic Replay
- In development validation, the deterministic test harness executes `SIMULATED_7_DAY_SCENARIO` across 12,650,000 synthetic flows.
- This validates reporting logic, math, and SLA checks, but **does not substitute for live operational observation**.
- In all reports and dashboards, synthetic scenarios are prominently labeled `SIMULATED_7_DAY_SCENARIO`.
- Real live observation is reported separately and marked `PENDING_AUTHORIZED_LIVE_DEPLOYMENT`.
