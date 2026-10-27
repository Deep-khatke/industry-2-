# Phase 1–8 Component & Dependency Inventory

## 1. Implemented & Verified Components

| Phase | Component Name | Source Location | Implementation Status | Integration Status |
|---|---|---|---|---|
| **Phase 1** | FlowEvent v1.2 Contract & Normalizer | `packages/contracts/flow_event.py` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 1** | IPFIX/NetFlow Binary Protocol Parser | `services/telemetry_collector/protocol.py` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 1** | MemoryStreamSink & Flow Adapters | `adapters/memory/sink.py` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 2** | FCS-UDIP Dataset Registry & Split Engine | `services/dataset_pipeline/src/fcs_data/` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 2** | FeatureSpec v1.2 & Leakage Prevention | `packages/contracts/features.py` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 3** | LightGBM Intrusion Detection Model | `services/ml_training/src/fcs_ml/models/` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 3** | Preprocessing Pipelines & Encoders | `services/ml_training/src/fcs_ml/pipeline/` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 4** | FastAPI REST & Event Backend | `services/api/src/fcs_api/app.py` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 4** | React SOC Dashboard (TypeScript/Vite) | `apps/security-dashboard/` | IMPLEMENTED | INTEGRATED & BUILD VERIFIED |
| **Phase 4** | Incident Manager & Deduplication Engine | `services/api/src/fcs_api/incidents/` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 4** | Manual Response Policy Engine | `services/api/src/fcs_api/response/policy.py` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 4** | Firewall Simulator & Rule Journal | `services/api/src/fcs_api/firewall/simulator.py` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 5** | FCS-HMD Hierarchical Router | `services/ml_training/src/fcs_ml/hmd/router.py` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 5** | Tenant IsolationForest Anomaly Detector | `services/ml_training/src/fcs_ml/hmd/anomaly.py` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 5** | Specialist Models (DDoS, Scanning) | `services/ml_training/src/fcs_ml/hmd/specialists/`| IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 5** | Evidence Fusion & DetectionBundle | `services/ml_training/src/fcs_ml/hmd/fusion.py` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 6** | Flower Federated Learning Client Cohort | `services/federated-learning/src/fcs_pfl/` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 6** | Differential Privacy Accountant | `services/federated-learning/src/fcs_pfl/privacy/`| IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 6** | SecAgg+ 5-of-7 Quorum Protocol Guard | `services/federated-learning/src/fcs_pfl/secagg/` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 7** | Dual-Signer (ECDSA + ML-DSA-65) | `services/governance/src/fcs_governance/crypto/` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 7** | MockFabricLedger & SmartBFT Consensus | `services/governance/src/fcs_governance/fabric/` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 7** | Model Rollback & Promotion Workflow | `services/governance/src/fcs_governance/workflow/` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 8** | Contract Matrix Validator (INT-01 - INT-20)| `tools/phase8/compatibility_checks/` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 8** | Fault Injection Engine (F01–F30) | `tools/phase8/fault_injector/engine.py` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 8** | Performance Metrics Collector (P0–P4) | `tools/phase8/metrics_collector/collector.py` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 8** | Multi-Tenant Traffic Scenario Runner | `tools/phase8/scenario_runner/runner.py` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 8** | Cryptographic Evidence Bundle Generator | `tools/phase8/evidence_generator/bundle.py` | IMPLEMENTED | INTEGRATED & TESTED |
| **Phase 8** | Unified Orchestrator CLI (`fcs`) | `tools/phase8/orchestrator/cli.py` | IMPLEMENTED | INTEGRATED & TESTED |

## 2. Production Prerequisites (Profile C — Blocked by Zero-Cost Policy)

The following components are deferred to Phase 9 and cannot be run in Phase 8 without violating the ₹0 budget or security boundaries:
1. **Live Border Router Exporters:** Physical Cisco/Juniper IPFIX export feeds (`REQUIRES_REAL_ISP_ENVIRONMENT`).
2. **Multi-AZ Cloud Stream Infrastructure:** AWS Kinesis / GCP PubSub multi-region streaming (`BLOCKED_BY_ZERO_COST_POLICY`).
3. **Multi-Account AWS VPC Peering:** Cross-tenant VPC isolation across independent billable accounts (`BLOCKED_BY_ZERO_COST_POLICY`).
4. **Physical Firewall ACL Enforcement:** Direct SSH/Netconf push to production BGP border routers (`PROHIBITED_IN_PHASE_8`).
5. **Multi-Organization Cloud Fabric Consensus:** 4 distinct physical cloud hosting providers for SmartBFT (`REQUIRES_REAL_ISP_ENVIRONMENT`).
6. **Automatic Response Mode (AUTO):** Disabled by policy until formal Phase 9 ISP shadow trial qualification (`BLOCKED_PENDING_INDEPENDENT_QUALIFICATION`).
