# Federated Cyber Shield (FCS) v1.2 — Production Hardening Architecture

## 1. Architectural Overview & System Planes

Federated Cyber Shield (FCS) Architecture v1.2 organizes autonomous cyber defense for multi-tenant Internet Service Providers (ISPs) across six strictly separated, independently survivable operational planes.

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
        SecAgg --> DPAccountant[Opacus DP-SGD (PRV Accounting &epsilon;, &delta;)]
        DPAccountant --> LocalTrainer[Local Gradient Computer]
    end

    subgraph GovernancePlane["4. GOVERNANCE PLANE"]
        ConsortiumRegistry[Model Candidate Registry] --> DualSigner[Dual ECDSA P-256 + ML-DSA-65 Signer]
        DualSigner --> Ledger[Hyperledger Fabric Immutable Commitments]
        Ledger --> CanonicalManifest[RFC 8785 Canonical JSON Manifests]
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

## 2. Plane Isolation & Decoupling Guarantees

1. **Data Plane vs. Detection Plane**: Ingestion operates asynchronously from model inference. An ingestion burst or temporary buffer backpressure never halts existing telemetry windows or drops active state.
2. **Federation Failure Survivability**: A federation coordinator crash or participant network partition never degrades detection. Active edge nodes continue real-time detection with the current verified model artifact.
3. **Ledger / Blockchain Decoupling**: Fabric peer downtime or network latency does not block telemetry inspection or local incident evaluation. Local nodes rely on cryptographically cached and verified release manifests.
4. **Specialist Model Resilience**: If a specialist classifier (e.g. DDoS or PortScan) experiences corrupt weights or latency timeouts, the dispatcher automatically cascades to the general detector, and ultimately to the rules-only fallback engine (`FCS-R101..104`).
5. **Post-Quantum Cryptography Isolation**: Post-quantum ML-DSA-65 verification operates strictly during model promotion and release packaging. High-throughput packet ingestion and feature scoring utilize optimized, sub-millisecond CPU kernels without cryptographic overhead.

---

## 3. Threat Surfaces and Trust Boundaries

- **Tenant Isolation**: 7 simulated ISP tenants (T01 through T07) maintain disjoint telemetry, alert subscriptions, and incident records. Cross-tenant access is blocked at the authentication, ORM, and database filtering layers.
- **Zero-Cost Foundation**: Designed, verified, and maintainable under strict ₹0 / $0 financial expenditure using standard open-source runtimes (Python 3.11+, TypeScript/Vite, SQLite, OpenTofu, Docker/Compose).
- **Gate G13 Invariant**: Autonomous direct router reconfiguration (`AUTO_LIVE`) remains strictly disabled in software configuration and architectural policy. All mitigation actions require explicit human operator approval via the Firewall Simulator.
