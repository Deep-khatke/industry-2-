# Federated Cyber Shield (FCS) v1.2 — Architecture Specification (Phase 1)

## 1. System Overview
Federated Cyber Shield (FCS) is a cloud-oriented, privacy-preserving cybersecurity telemetry platform purpose-built for rural Internet Service Providers (ISPs). Phase 1 delivers the foundational data contracts, multi-tenant isolation primitives, IPFIX/NetFlow v9 collector, synthetic traffic generator, streaming abstraction, and static infrastructure definitions.

---

## 2. Future Production AWS Architecture
The planned production architecture is defined via modular OpenTofu IaC modules. The deployment operates in **definition-only mode** during Phase 1 to guarantee ₹0 expenditure.

```mermaid
graph TB
    subgraph ISP_Edge [Rural ISP Edge Networks]
        ExpA["Router Exporter A<br/>10.100.1.1 (Domain 101)"]
        ExpB["Router Exporter B<br/>10.100.2.1 (Domain 102)"]
    end

    subgraph AWS_Ingress [AWS Cloud - Ingress Tier]
        NLB["AWS Network Load Balancer<br/>UDP Port 2055 (Multi-AZ)"]
        SG["Ingress Security Group<br/>(Restricted to ISP Subnets)"]
    end

    subgraph AWS_Processing [AWS Cloud - Private Processing Tier]
        Collector["FCS Telemetry Collector<br/>(RFC 7011 / 3954 Parser)"]
        Registry["Tenant Registry<br/>(Origin Binding)"]
        Normalizer["Normalizer & Privacy Mask<br/>(Subnet Masking)"]
    end

    subgraph AWS_Streaming [AWS Cloud - Streaming Tier]
        Kinesis["Amazon Kinesis Data Streams<br/>(Tenant-Scoped Shards, KMS Encrypted)"]
    end

    subgraph AWS_Storage [AWS Cloud - Storage Tier]
        S3["Amazon S3 Archival Bucket<br/>(TLS-Only, KMS Customer Managed Keys)"]
    end

    subgraph AWS_KMS [AWS Cloud - Cryptographic Boundaries]
        KMSA["KMS Key: tenant-isp-alpha"]
        KMSB["KMS Key: tenant-isp-beta"]
    end

    ExpA -->|UDP 2055| NLB
    ExpB -->|UDP 2055| NLB
    NLB --> SG --> Collector
    Collector --> Registry
    Collector --> Normalizer
    Normalizer -->|FlowEvent v1| Kinesis
    Kinesis --> S3
    KMSA -.->|Enforce Isolation| Kinesis
    KMSB -.->|Enforce Isolation| Kinesis
```

---

## 3. Phase 1 Free Simulation Architecture (Level A)
To eliminate cloud costs entirely, Phase 1 simulates the entire ingestion and streaming lifecycle in the workspace using open-source, thread-safe components:

```mermaid
graph LR
    subgraph Synthetic_Generation [Tools Tier]
        Generator["SyntheticTrafficGenerator<br/>(Normal & Fault Scenarios)"]
        Replayer["TrafficReplayer"]
    end

    subgraph Collector_Pipeline [Services Tier]
        Parser["IPFIXParser<br/>(Binary RFC 7011/3954)"]
        SeqTrack["SequenceTracker<br/>(Gap & Loss Detection)"]
        TmplCache["TemplateCache<br/>(Domain Isolated)"]
        TenRegistry["TenantRegistry<br/>(7 Rural ISPs)"]
        Norm["TelemetryNormalizer<br/>(Privacy /24 Mask)"]
    end

    subgraph Stream_Sinks [Adapters Tier]
        MemSink["MemoryStreamSink<br/>(Fast Validation & Faults)"]
        SqliteSink["SQLiteStreamSink<br/>(WAL Mode, Replay Persistence)"]
        KinesisStub["KinesisStreamSink<br/>(Disabled / Offline Mockable)"]
    end

    subgraph Observability [Observability Tier]
        Metrics["MetricsCollector<br/>(Thread-Safe)"]
        Coverage["CoverageTracker<br/>(Degraded State Visibility)"]
        Audit["AuditLogger<br/>(SHA-256 Hash Chain)"]
    end

    Generator --> Replayer
    Replayer --> Parser
    Parser --> TmplCache
    Parser --> SeqTrack
    Parser --> TenRegistry
    TenRegistry --> Norm
    Norm -->|FlowEvent v1| MemSink
    Norm -->|FlowEvent v1| SqliteSink
    Parser --> Metrics
    SeqTrack --> Coverage
    TenRegistry --> Audit
```

---

## 4. Trust Boundaries & Tenant Isolation
1. **Physical Exporter Resolution**: Incoming packets are mapped to a tenant via authenticated exporter IP and Observation Domain ID.
2. **Untrusted Metadata Rejection**: Claims embedded inside telemetry packets that contradict trusted configuration raise `UntrustedTenantClaimViolation` and are dropped.
3. **RBAC Isolation**:
   - `TENANT_ADMIN` & `TENANT_ANALYST`: Scoped exclusively to their own tenant ID.
   - `PLATFORM_ADMIN`: Manages tenancy metadata and platform health. Strictly prohibited from reading raw telemetry records.
4. **Subscriber Privacy**: IP addresses are masked to `/24` network prefixes. Raw host subscriber identifiers are never stored.

---

## 5. Separation of Implementations vs Cloud Deployments
| Layer | Implemented in Phase 1 | Status | Real Cloud Deployment |
|---|---|---|---|
| **Data Contracts** | Pydantic FlowEvent v1, JSON canonical, hash | Complete & Tested | N/A (Portable) |
| **Collector Parser** | Binary IPFIX & NetFlow v9 parser, template cache | Complete & Tested | Runs on dev/test compute |
| **Stream Adapter** | MemoryStreamSink & SQLiteStreamSink | Complete & Tested | Ephemeral & local persistence |
| **AWS Kinesis Adapter** | Isolated adapter, partition key scoping, mockable | Complete (Disabled) | `BLOCKED_BY_ZERO_COST_POLICY` |
| **OpenTofu Modules** | 8 reusable modules (networking, IAM, S3, KMS, etc.) | Formatted & Validated | `BLOCKED_BY_ZERO_COST_POLICY` |
| **AWS Accounts & IAM** | Policy logic & least-privilege definitions | Statically Verified | `BLOCKED_BY_ZERO_COST_POLICY` |
