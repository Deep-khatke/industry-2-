# Federated Cyber Shield (FCS) v1.2 — Integrated System Architecture

## 1. Architectural Scope & Mission
Phase 8 integrates and verifies all functioning components developed across Phases 1 through 7 of the Federated Cyber Shield (FCS v1.2) platform. The primary mission is to establish cross-component contract compatibility, verify multi-tenant isolation across seven simulated Tier-1/Regional ISP participants, enforce defensive manual response invariants, validate federated privacy controls, and confirm resilient operational recovery under controlled failure injection.

## 2. End-to-End Logical Data Flow
The platform partitions responsibilities into two decoupled planes: the **Per-Event Detection Plane** and the **Training & Governance Plane**.

```
[SYNTHETIC / AUTHORIZED ISP FLOW EXPORTS]
                │
                ▼
      [IPFIX / NetFlow COLLECTOR]
                │
                ▼ (FlowEvent v1.2)
     [TENANT STREAM ADAPTER (MemorySink)]
                │
                ▼
       [FEATURE WINDOW ENGINE]
                │ (Window Aggregations)
                ▼
     [FEATURESPEC v1.2 VALIDATION CHECK]
                │ (14 Locked Deployable Features)
                ▼
     [FCS-HMD HIERARCHICAL INFERENCE ENGINE]
      ├── Level 1: LightGBM General Intrusion Detector
      ├── Level 1: IsolationForest Tenant Anomaly Profiler
      └── Level 2: Conditional Specialist Routing
            ├── DDoS Specialist (Rate & Port Entropy Triggers)
            └── Scanning Specialist (SYN Ratio & Destination Triggers)
                │
                ▼
         [EVIDENCE FUSION] (Weighted Borda / Short-Circuit)
                │ (DetectionBundle v1.2)
                ▼
         [INCIDENT ENGINE] (Deduplication Window & History)
                │
                ▼
        [SQLITE PERSISTENT STORE]
                │
                ▼
       [FASTAPI BACKEND] ──► [REACT SOC DASHBOARD]
                │
                ▼
    [MANUAL RESPONSE POLICY ENGINE] (Human Approval Check)
                │ (Approved Temporary Block / Rate Limit)
                ▼
     [FIREWALL SIMULATOR] (Simulated Rule Enforcement)
```

## 3. Decoupled Training & Governance Plane
```
[7 SIMULATED ISP TENANTS]
         │ (Private Local Telemetry Windows)
         ▼
[FLOWER COHORT COORDINATOR]
         │ (Opacus DP-SGD: Epsilon <= 10.0, Delta <= 1e-5)
         ▼
[SECAGG+ PROTOCOL] (5-of-7 Quorum Required)
         │ (Aggregated Global Weights)
         ▼
[CANDIDATE MODEL REGISTRY]
         │ (Evaluation & Dual Review)
         ▼
[DUAL-SIGNING ENGINE] (ECDSA P-256 + ML-DSA-65 over RFC 8785)
         │ (DualSignedReleaseManifest)
         ▼
[FABRIC CONSORTIUM LEDGER] (SmartBFT 4-Orderer Consensus)
         │ (Committed Transaction Receipt)
         ▼
[TENANT-CONTROLLED ACTIVATION] (Local Independent Sovereign Choice)
```

## 4. Plane Decoupling & Availability Invariants
1. **Zero Blocking Calls on Ingestion Path:** The detection path (`FlowEvent -> Window -> HMD -> Incident`) contains no blocking network calls to the Flower federation coordinator, the Fabric consortium blockchain, or post-quantum key generation services.
2. **Degraded Inference Modes:** If the hierarchical router or specialists time out or fail, the system deterministically degrades to Level-1 General Detector + Anomaly, or to deterministic `RULES_ONLY` fallback.
3. **Response Policy Mode:** Manual Response Mode is permanently enforced. The execution parameter `network_action_executed` is strictly `False`. Real hardware router ACLs are simulated via `simulated_firewall_rules`.
4. **Strict Zero-Cost Policy:** ₹0 / $0 spend. All services execute locally on free standard development infrastructure and eligible GitHub Actions free runners.
