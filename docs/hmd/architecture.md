# FCS-HMD Subsystem Architecture (Version 1.2)
## Hierarchical Multi-Model Intrusion Detection Engine

**System:** Federated Cyber Shield (FCS)  
**Subsystem:** FCS-HMD (Hierarchical Multi-Model Detection Engine)  
**Architecture Baseline:** v1.2  
**Financial Budget:** Strictly ₹0.00 / $0.00 (Zero-Cost Local CPU Execution)  

---

## 1. System Overview & Purpose

The FCS-HMD subsystem replaces monolithic single-model intrusion detection pipelines with a modular, 4-tier hierarchical defense topology. Rather than executing computationally expensive specialists across all network traffic, FCS-HMD decouples detection into:
1. **Level 1 General Threat Screening:** Broad detection of known anomalous flow profiles (`lightgbm_deployable_subset`).
2. **Level 1 Tenancy-Isolated Anomaly Detection:** ISP-specific benign behavioral profiles (`isolationforest_anomaly_tenant` and `autoencoder_anomaly`).
3. **Conditional Specialist Routing:** Feature- and score-triggered dispatch of lightweight attack specialists (`lightgbm_ddos_specialist` and `lightgbm_scanning_specialist`).
4. **Deterministic Evidence Fusion:** Bayesian synthesis combining Level 1 probabilities, specialist dominance ($\ge 0.85$), and behavioral rule risk floors into actionable threat intelligence.

```text
                    ISP NETWORK TELEMETRY
                              |
                              v
                        FlowEvent v1
                              |
                              v
                    FEATURE WINDOW ENGINE (30s)
                              |
                              v
                     FEATURE VALIDATION (14-dim)
                              |
                              v
                 HIERARCHICAL DETECTION
                              |
                +-------------+-------------+
                |                           |
                v                           v
       GENERAL DETECTION             LOCAL ANOMALY
             MODEL                       MODEL
       (LightGBM Subset)             (Isolation Forest)
                |                           |
                +-------------+-------------+
                              |
                              v
                       MODEL ROUTER
                  (24.9 us p95 Overhead)
                              |
                +-------------+-------------+
                |             |             |
                v             v             v
             DDoS         SCANNING       OPTIONAL
          SPECIALIST     SPECIALIST      BOTNET
         (Volumetric)     (SYN Probe)   (Ineligible)
                |             |             |
                +-------------+-------------+
                              |
                              v
                     EVIDENCE COLLECTION
                              |
                              v
                  CALIBRATION VALIDATION
                              |
                              v
                   EVIDENCE FUSION ENGINE
             (Deterministic Bayesian Synthesis)
                              |
                              v
                     THREAT ASSESSMENT
                              |
                              v
                       INCIDENT ENGINE
                              |
                              v
                   SECURITY DASHBOARD (React)
                              |
                              v
                  RESPONSE RECOMMENDATIONS
                              |
                              v
                   MANUAL ADMIN APPROVAL (Mandatory)
                              |
                              v
                     FIREWALL SIMULATOR
```

---

## 2. Core Architectural Principles

1. **Role Specialization:** Each model addresses a discrete threat domain; models do not make uncalibrated inferences outside their validated envelope.
2. **Deterministic Explainability:** Evidence fusion uses auditable Bayesian weights and rule risk floors rather than opaque deep meta-models.
3. **Graceful Degradation:** A specialist timeout or exception degrades to Level 1 general screening; failures never produce fabricated benign scores.
4. **Tenancy Isolation:** Anomaly models are fit solely on benign partitions per ISP and stored in tenant-isolated directories. They are never shared or federated across tenants.
5. **Strict Safety Invariant:** All ML models output probabilistic evidence only (`network_action_executed = False`). Autonomous firewall actuation (`AUTO`) remains permanently disabled.
6. **Zero-Cost Constraint:** Operates entirely on standard CPU compute without paid cloud or API dependencies.
