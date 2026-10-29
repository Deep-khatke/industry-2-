# Federated Cyber Shield (FCS) v1.2
## Autonomous Cybersecurity Intelligence & Threat Mitigation Platform for Rural ISPs

[![Zero-Cost Compliant](https://img.shields.io/badge/Budget-%E2%82%B90%20%2F%20%240-brightgreen.svg)](#zero-cost-policy)
[![Tests Passing](https://img.shields.io/badge/Tests-360%2F360%20Passed-success.svg)](#automated-testing)
[![Phase 11 Complete](https://img.shields.io/badge/Release%20Candidate-v1.2.0--rc1%20(Phase%2011)-blue.svg)](PHASE11_COMPLETION_REPORT.md)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](#development-setup)
[![React 18](https://img.shields.io/badge/React-18%20%7C%20TypeScript%20%7C%20Vite-61dafb.svg)](#security-operations-dashboard)
[![Gate G13](https://img.shields.io/badge/Gate%20G13%20(AUTO_LIVE)-BLOCKED-red.svg)](#safety-invariants)
[![License](https://img.shields.io/badge/License-Apache%202.0-lightgrey.svg)](LICENSE)

Federated Cyber Shield (FCS) is a cloud-oriented, privacy-preserving cybersecurity intelligence and threat-mitigation platform designed specifically for rural Internet Service Providers (ISPs).

---

## Complete Phase 1–11 Capability Matrix

| Phase | Subsystem | Status | Key Capabilities |
| :--- | :--- | :---: | :--- |
| **Phase 1** | Cloud Foundation & Telemetry Ingestion | **VERIFIED** | IPFIX/NetFlow v9 parsing, subscriber IP anonymization, sequence tracking, multi-tenant isolation for 7 ISPs. |
| **Phase 2** | Unified Dataset Intelligence (FCS-UDIP) | **VERIFIED** | NF-UNSW-NB15 / NF-BoT-IoT integration, deterministic partitioning, feature contract validation. |
| **Phase 3** | Machine Learning Training & Evaluation | **VERIFIED** | Candidate model registry, `lightgbm_deployable_subset` selection (0.953 PR-AUC). |
| **Phase 4** | Threat Detection & SOC Dashboard | **VERIFIED** | 30s feature windows, sub-millisecond CPU ML inference, rules FCS-R101..104, React SOC UI, human-in-the-loop firewall simulation. |
| **Phase 5** | Hierarchical Model Dispatcher (HMD) | **VERIFIED** | Sub-25ms inference, specialist routing (DDoS, Scan, Anomaly), fallback cascade. |
| **Phase 6** | Differential Privacy & Federated Learning | **VERIFIED** | SecAgg+ masked vector exchange, Opacus DP-SGD, Rényi/PRV cumulative accounting. |
| **Phase 7** | Post-Quantum Cryptography & Governance | **VERIFIED** | Dual ECDSA P-256 + NIST ML-DSA-65 signatures, Hyperledger Fabric immutable commitments. |
| **Phase 8** | System Hardening & Performance | **VERIFIED** | System contract matrix, failure injection matrix, SLO performance verification. |
| **Phase 9** | Real ISP Pilot Operations | **VERIFIED** | 7-day shadow evaluation protocol, multi-tenant incident escalation, operator runbooks. |
| **Phase 10** | Automatic Response Safety Handoff | **GATED** | Automated mitigation qualification specification; Gate G13 strictly held in BLOCKED state. |
| **Phase 11** | **Production Hardening & DevSecOps** | **VERIFIED (DEV RC)** | **Zero-cost audit, CycloneDX/SPDX SBOMs, atomic DR, dual-signed release manifest, 8 CI/CD workflows.** |

---

## Production Hardening Architecture

```mermaid
flowchart TD
    subgraph DataPlane["1. DATA PLANE"]
        IPFIX[IPFIX / NetFlow v9 Exporters] --> Ingestion[Zero-Allocation Ingestion & Validator]
        Ingestion --> FeatureWindow[Feature Window Aggregator (43 Canonical Features)]
        FeatureWindow --> EventBus[Durable In-Memory / SQLite Event Queue]
    end

    subgraph DetectionPlane["2. DETECTION PLANE"]
        EventBus --> Router[Hierarchical Model Dispatcher]
        Router --> Rules[Deterministic Rules Engine (FCS-R101..104)]
        Router --> HMD[Hierarchical LightGBM Ensemble]
        Router --> Anomaly[Isolation Forest Anomaly Specialist]
        Rules & HMD & Anomaly --> Fusion[Evidence Fusion & Threat Scorer]
        Fusion --> Degrade[Safe Fallback Engine (RULES_ONLY on Corruption)]
    end

    subgraph LearningPlane["3. LEARNING PLANE"]
        FederationMgr[Flower 7-Client Cohort Manager] --> SecAgg[SecAgg+ Masked Vector Exchange]
        SecAgg --> DPAccountant[Opacus DP-SGD (PRV Accounting)]
        DPAccountant --> LocalTrainer[Local Gradient Computer]
    end

    subgraph GovernancePlane["4. GOVERNANCE PLANE"]
        ConsortiumRegistry[Model Candidate Registry] --> DualSigner[Dual ECDSA P-256 + ML-DSA-65 Signer]
        DualSigner --> CanonicalManifest[RFC 8785 Canonical JSON Manifests]
    end

    subgraph ResponsePlane["5. RESPONSE PLANE"]
        Degrade --> IncidentLedger[Multi-Tenant Incident Ledger]
        IncidentLedger --> ApprovalEngine[Manual Response Gate (RBAC: Security Admin)]
        ApprovalEngine --> FirewallSim[Firewall Simulator (Allowlist & Duration Bounds)]
        ApprovalEngine -.-> BlockedGate["[BLOCKED] Gate G13 (AUTO_LIVE)"]
    end

    subgraph OperationsPlane["6. OPERATIONS PLANE"]
        Prometheus[Prometheus Metrics (/metrics)]
        HealthEndpoint[Health & Profile Check (/health)]
        BackupMgr[SQLite Atomic Online Backup Manager]
        RestoreValidator[Sandboxed Restore & Privacy Invariant Validator]
    end
```

---

## Free Development Setup

FCS requires **zero paid services, cloud subscriptions, or commercial APIs**.

### Prerequisites
- Python 3.11, 3.12, or 3.13
- Node.js 18+ or 20+ and npm
- OpenTofu v1.6+ (or read-only Terraform)
- Git 2.30+

### Setup Instructions
```bash
# 1. Clone repository
git clone https://github.com/Deep-khatke/industry-2-.git
cd "industry 2"

# 2. Install workspace dependencies
pip install -e packages/contracts
pip install -e services/telemetry_validation
pip install -e services/dataset_pipeline
pip install -e services/ml_training
pip install -e services/api
pip install -e services/federated-learning
pip install -e services/governance
pip install -e services/pilot-management
pip install -e . --no-deps

# 3. Build React Security Dashboard
cd apps/security-dashboard
npm install
npm run build
cd ../..
```

---

## Operational CLI & Demonstration Commands

> [!NOTE]
> Demonstration accounts and endpoints are strictly scoped to the `DEVELOPMENT` environment profile and are automatically rejected in staging and production reference modes.

```bash
# Seed development database with 7 ISP tenants and demo accounts (DEV ONLY)
fcs demo seed

# Start the unified backend server (FastAPI API + static React SOC UI)
fcs api start --port 8000

# Open browser at http://127.0.0.1:8000/
# Login with: responder_alpha / FcsDemo2026! (Development Profile Only)

# Trigger synthetic telemetry replay scenarios
fcs demo replay --scenario normal --tenant rural-isp-alpha       # Benign traffic (0 false alarms)
fcs demo replay --scenario suspicious --tenant rural-isp-alpha   # Volumetric DDoS flood (CRITICAL alert)
fcs demo replay --scenario scanning --tenant rural-isp-alpha     # SYN port sweep (MEDIUM alert)

# Reset demo database
fcs demo reset
```

---

## Unified Verification & Release Gates (Phase 11)

```bash
# Run full monorepo regression suite (360 tests)
python -m pytest tests/ -v

# Run unified Phase 11 release verification and gate evaluation
python scripts/verify_phase11.py

# Run static zero-cost security scanner
python tools/zero-cost-audit/scanner.py
```

### Release Gates Summary (G01 – G15)
- **G01 — Tenant Boundaries:** **PASS_DEVELOPMENT** (7-ISP isolation, RBAC, IDOR prevention).
- **G02 — Ingestion:** **PASS_DEVELOPMENT** (IPFIX normalization, timestamp checks).
- **G03 — Durable Delivery:** **PASS_DEVELOPMENT** (SQLite WAL persistence, zero loss).
- **G04 — Learning Privacy:** **PASS_DEVELOPMENT** (SecAgg+ masked aggregation across 7 clients).
- **G05 — Differential Privacy:** **PASS_DEVELOPMENT** (Opacus DP-SGD, non-resettable spend).
- **G06 — Model Safety:** **PASS_DEVELOPMENT** (LightGBM candidate parity, CPU execution).
- **G07 — Detection Utility:** **PASS_DEVELOPMENT** (FCS-R101..104, zero false alarms on normal traffic).
- **G08 — Manual Response:** **PASS_DEVELOPMENT** (Human approval, protected targets, TTL bounds).
- **G09 — Reliability & Recovery:** **PASS_DEVELOPMENT** (Sub-second RTO: 0.032s, rules fallback).
- **G10 — Ledger Governance:** **PASS_DEVELOPMENT** (Dual ECDSA P-256 + ML-DSA-65 release signatures).
- **G11 — Supply Chain Security:** **PASS_DEVELOPMENT** (CycloneDX 1.5 & SPDX 2.3 SBOMs).
- **G12 — Post-Quantum Isolation:** **PASS_DEVELOPMENT** (ML-DSA-65 restricted to governance layer).
- **G13 — Autonomous Response:** **BLOCKED** (Direct physical router mitigation disabled).
- **G14 — Dataset Lineage:** **PASS_DEVELOPMENT** (Provenance tracking, leakage prevention).
- **G15 — Hierarchical ML Latency:** **PASS_DEVELOPMENT** (HMD p50 latency < 12ms).

---

## Documentation Index

- [Phase 11 Completion Report](PHASE11_COMPLETION_REPORT.md)
- [Final System Verification Report](FINAL_SYSTEM_VERIFICATION_REPORT.md)
- [Final Production Readiness Assessment](FINAL_PRODUCTION_READINESS_ASSESSMENT.md)
- [Production Hardening Architecture](docs/production/architecture.md)
- [Deployment Reference](docs/production/deployment-reference.md)
- [Production Blockers & Hardware Qualification](docs/production/production-blockers.md)
- [Final Security Threat Model](docs/security/final-threat-model.md)
- [Vulnerability & Dependency Audit](docs/security/vulnerability-audit.md)
- [Multi-Tenant Isolation Guarantees](docs/security/tenant-isolation.md)
- [Model Artifact Security](docs/security/model-artifact-security.md)
- [Defensive Response Safety](docs/security/response-safety.md)
- [DevSecOps CI/CD Architecture](docs/devsecops/ci-cd-architecture.md)
- [Software Bill of Materials (SBOM)](docs/devsecops/sbom.md)
- [Service Level Objectives (SLOs)](docs/reliability/service-objectives.md)
- [Disaster Recovery Plan](docs/reliability/disaster-recovery-plan.md)
- [Operator Runbook](docs/operations/operator-runbook.md)
- [Master Emergency Disable Protocol](docs/operations/emergency-disable.md)

---

## License
Apache License 2.0. Copyright (c) 2026 Federated Cyber Shield Architecture Team.
