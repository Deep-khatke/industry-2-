# Phase 8 Threat Model & Attack Surface Analysis

## 1. System Threat Context
Federated Cyber Shield (FCS v1.2) is a multi-tenant, federated collaborative cybersecurity platform across seven independent Internet Service Providers (ISPs). The threat model addresses adversarial threats targeting telemetry ingestion, feature window processing, hierarchical machine learning inference, incident management, defensive manual action execution, federated weight aggregation, and consortium governance.

## 2. Trust Boundaries & Perimeters
```
[External Exporters / Untrusted Network]
         │ (Perimeter 1: Telemetry Parser & Normalizer)
         ▼
[Tenant Ingestion Plane (MemorySink)]
         │ (Perimeter 2: Tenant Isolation & FeatureSpec Gate)
         ▼
[Hierarchical Detection Engine (FCS-HMD)]
         │ (Perimeter 3: Model Integrity & Version Digest Gate)
         ▼
[Incident & Storage Layer (SQLite / Outbox)]
         │ (Perimeter 4: RBAC & Tenant Scoped JWT Sessions)
         ▼
[Manual Response Center & Firewall Simulator]
         │ (Perimeter 5: Dual Human Approval & Scoping Check)
         ▼
[Simulated Network Devices]
```

Training & Governance Perimeter:
```
[Client Local Models] ──(Perimeter 6: DP-SGD Budget & Opacus Guard)──► [Local Updates]
[Local Updates]       ──(Perimeter 7: SecAgg+ Masked Vectors)      ──► [Aggregator]
[Aggregated Candidate]──(Perimeter 8: Dual Signatures & RFC 8785)  ──► [Governance Ledger]
```

## 3. Attack Surfaces & Defensive Mitigations

| Attack Surface | Threat Scenario | Implemented Mitigation | Verification Evidence |
|---|---|---|---|
| **Telemetry Ingestion** | Malformed IPFIX frames, truncated binary headers, buffer overruns | Strict binary header bounds checking, parser error quarantining | `tests/system/security/test_adversarial_security.py::test_malformed_telemetry_rejection` |
| **Multi-Tenant State** | Cross-tenant IDOR object access to incidents and rules | Mandatory backend tenant scoping on all SQL queries independent of frontend claims | `tests/system/security/test_adversarial_security.py::test_cross_tenant_idor_incident_access` |
| **Response Engine** | Unauthorized automated rule push or role escalation | READ_ONLY role checks enforced; Automatic Mode permanently disabled | `tests/system/security/test_adversarial_security.py::test_unauthorized_role_escalation` |
| **Hierarchical ML** | Feature injection, poisoned or mismatched model weights | FeatureSpec schema digest validation; SHA-384 artifact hash matching; fallback to rules-only | Faults F04, F05, F06 |
| **Federated Learning** | Plaintext model reconstruction, subscriber privacy leakage | Opacus DP-SGD with cumulative epsilon ceiling (10.0); SecAgg+ masked vectors; no plaintext logging | `tests/system/privacy/test_multi_tenant_privacy.py` |
| **Consortium Governance** | Forged model manifests, key compromise, unapproved model activation | RFC 8785 canonicalization, dual signing (ECDSA P-256 + ML-DSA-65), SmartBFT 4-orderer consensus | `tests/system/security/test_adversarial_security.py::test_tampered_model_manifest_dual_signature` |

## 4. Residual Risks & Production Requirements
1. **Physical Account Isolation:** In Phase 8, tenant isolation is verified via software-enforced tenant IDs and schema keys within shared SQLite storage. Production Phase 9 requires separate AWS accounts and VPC peering.
2. **Hardware Router State Drift:** Simulated firewall actions verify internal rule tables; live Phase 9 requires out-of-band Netconf/BGP flowspec telemetry validation to confirm device TTL expiration.
3. **Automatic Response Safety (AUTO):** AUTO remains permanently disabled. A formal seven-day shadow evaluation trial on live ISP traffic is mandatory prior to enabling automated rule execution.
