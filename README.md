# Federated Cyber Shield (FCS) v1.2
## Autonomous Cybersecurity Intelligence & Threat Mitigation Platform for Rural ISPs

[![Zero-Cost Compliant](https://img.shields.io/badge/Budget-%E2%82%B90%20%2F%20%240-brightgreen.svg)](#zero-cost-policy)
[![Tests Passing](https://img.shields.io/badge/Tests-156%2F156%20Passed-success.svg)](#automated-testing)
[![Phase 4 Complete](https://img.shields.io/badge/Phase%204-Verified%20MVP-blue.svg)](file:///c:/college/industry%202/PHASE4_COMPLETION_REPORT.md)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](#development-setup)
[![React 18](https://img.shields.io/badge/React-18%20%7C%20TypeScript%20%7C%20Vite-61dafb.svg)](#security-operations-dashboard)
[![License](https://img.shields.io/badge/License-Apache%202.0-lightgrey.svg)](LICENSE)

Federated Cyber Shield (FCS) is a cloud-oriented, privacy-preserving cybersecurity intelligence and threat-mitigation platform designed specifically for rural Internet Service Providers (ISPs).

---

## Phase 1–4 Capability Matrix

| Phase | Subsystem | Status | Key Capabilities |
| :--- | :--- | :---: | :--- |
| **Phase 1** | Cloud Foundation & Telemetry Ingestion | **VERIFIED** | IPFIX/NetFlow v9 parsing, subscriber IP anonymization, sequence tracking, multi-tenant isolation for 7 ISPs. |
| **Phase 2** | Unified Dataset Intelligence (FCS-UDIP) | **VERIFIED** | NF-UNSW-NB15 / NF-BoT-IoT integration, deterministic partitioning, feature contract validation. |
| **Phase 3** | Machine Learning Training & Evaluation | **VERIFIED** | Benchmark experiments E3-01..E3-09, candidate model registry, `lightgbm_deployable_subset` selection (0.953 PR-AUC). |
| **Phase 4** | Threat Detection, SOC Dashboard & Manual Response | **VERIFIED** | 30s feature windows, sub-millisecond CPU ML inference, rules FCS-R101..104, React SOC UI, human-in-the-loop firewall simulation. |

---

## Architecture Overview

```text
         SIMULATED / AUTHORIZED ISP TELEMETRY
                         |
                         v
                 IPFIX / NETFLOW COLLECTOR
                         |
                         v
                  INPUT VALIDATION
                         |
                         v
                DURABLE EVENT ADAPTER
                         |
                         v
                FEATURE WINDOW ENGINE (30s event-time, 60s lateness)
                         |
                         v
               VERIFIED ML INFERENCE (LightGBM Deployable Subset, 14 NetFlow features)
                         |
                         v
               THREAT DETECTION RULES (FCS-R101..R104)
                         |
                         v
                  RISK ASSESSMENT (Composite Risk Scoring & Classification)
                         |
                         v
                   INCIDENT ENGINE (Grouping, Deduplication, Lifecycle)
                         |
              +----------+----------+
              |                     |
              v                     v
       INCIDENT DATABASE      NOTIFICATION OUTBOX
              |                     |
              +----------+----------+
                         |
                         v
                FASTAPI BACKEND (/v1/* REST API with RBAC & Tenant Scoping)
                         |
                         v
              REACT SECURITY DASHBOARD (7 SOC Views, Live Polling)
                         |
                         v
              ACTION RECOMMENDATIONS (Temporary Block, Rate Limit, Deep Inspection)
                         |
                         v
             HUMAN ADMINISTRATOR APPROVAL (SECURITY_RESPONDER / TENANT_ADMIN)
                         |
                         v
                RESPONSE POLICY ENGINE (Protected IP Guardrails, TTL Constraints)
                         |
                         v
                FIREWALL SIMULATOR (Isolated Software Engine, Rule Verification)
                         |
                         v
              VERIFY + AUDIT + UPDATE (Rollback Capability, Incident MITIGATED)
```

---

## Free Development Setup

FCS requires **zero paid services, cloud subscriptions, or credit cards**.

### Prerequisites
- Python 3.11, 3.12, or 3.13
- Node.js 18+ and npm
- OpenTofu v1.6+ (or Terraform in read-only mode)
- Git 2.30+

### Setup Instructions
```bash
# 1. Clone repository
git clone <repository-url>
cd "industry 2"

# 2. Install Python dependencies
pip install -r requirements-dev.txt
pip install -e .

# 3. Build React Security Dashboard
cd apps/security-dashboard
npm install
npm run build
cd ../..
```

---

## Quickstart & Operational CLI Commands

Federated Cyber Shield includes a unified CLI tool (`fcs`):

```bash
# Seed development database with 7 ISP tenants and demo accounts
fcs demo seed

# Start the unified backend server (FastAPI API + static React SOC UI)
fcs api start --port 8000

# Open browser at http://127.0.0.1:8000/
# Login with: responder_alpha / FcsDemo2026!

# Trigger synthetic telemetry replay scenarios
fcs demo replay --scenario normal --tenant rural-isp-alpha       # Benign traffic (0 false alarms)
fcs demo replay --scenario suspicious --tenant rural-isp-alpha   # Volumetric DDoS flood (CRITICAL alert)
fcs demo replay --scenario scanning --tenant rural-isp-alpha     # SYN port sweep (MEDIUM alert)

# Reset demo database to pristine initial state
fcs demo reset
```

---

## Security Operations Dashboard

The dashboard provides a Security Operations Center (SOC) interface featuring 7 views:

1. **Security Overview:** Real-time KPI metrics, active incidents, threat category distribution, and telemetry processing rates.
2. **Real-Time Threat Feed:** Live event-time anomaly stream with rule matches and ML inference scores.
3. **Incident Management:** Searchable incident ledger with status filters, forensic evidence drawer, and lifecycle transitions.
4. **Manual Response Center:** Actionable defensive recommendations, administrator approval modal, active firewall rules, and action audit journal.
5. **ISP Network Health:** Exporter freshness, ingestion delay, sequence gap detection, and monitoring completeness indicators.
6. **Model Monitoring:** Active candidate model metadata, feature contract parity table, and sub-millisecond CPU latency statistics.
7. **Settings:** Tenant profile, RBAC permissions matrix, protected target allowlist, and autonomous response disabled warning.

---

## Automated Verification & Release Gates

```bash
# Run complete Phase 4 verification & evaluate Architecture Gates G01..G08
python scripts/verify_phase4.py

# Run all 156 automated tests across monorepo
python -m pytest tests/ -v
```

### Release Gates Summary
- **G01 — Tenant Boundaries:** **PASS** (7-ISP simulated isolation, RBAC, IDOR prevention).
- **G02 — Ingestion:** **PASS** (NetFlow/IPFIX normalization, timestamp validation, deduplication).
- **G03 — Durable Delivery:** **PASS** (Window checkpoints, SQLite WAL persistence, outbox pattern).
- **G06 — Model Safety:** **PASS** (Candidate model verification, 14-feature parity, `network_action_executed = False`).
- **G07 — Detection:** **PASS** (Rules FCS-R101..104, risk assessment, zero false positive normal replay).
- **G08 — Manual Response:** **PASS** (Human approval enforced, protected targets, TTL, rollback, audit journal).
- **G13 — AUTO Response:** **NOT_APPLICABLE** (Strictly disabled in Phase 4).

---

## Documentation Index

- [Phase 4 Architecture Specification](file:///c:/college/industry%202/docs/architecture/phase4.md)
- [Manual Response Policy Specification](file:///c:/college/industry%202/docs/security/manual-response-policy.md)
- [Multi-Tenant Authorization Specification](file:///c:/college/industry%202/docs/security/tenant-authorization.md)
- [Incident Management Operations Guide](file:///c:/college/industry%202/docs/operations/incident-management.md)
- [Telemetry Monitoring Guide](file:///c:/college/industry%202/docs/operations/telemetry-monitoring.md)
- [Model Failure Recovery Guide](file:///c:/college/industry%202/docs/operations/model-failure-recovery.md)
- [Development Demonstration Guide](file:///c:/college/industry%202/docs/operations/development-demo.md)
- [Phase 4 Verification Report](file:///c:/college/industry%202/docs/phase-reports/phase4-verification.md)
- [Phase 5 Handoff Specification](file:///c:/college/industry%202/docs/phase-reports/PHASE5_HANDOFF.md)
- [Phase 4 Completion Report](file:///c:/college/industry%202/PHASE4_COMPLETION_REPORT.md)

---

## License
Apache License 2.0. Copyright (c) 2026 Federated Cyber Shield Architecture Team.
