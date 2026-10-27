# Phase 8 Handoff Specification
**Federated Cyber Shield (FCS) — Phase 7 to Phase 8 Transition**
*Production Hardening, Multi-Cloud Deployment & Rural ISP Pilot*

---

## 1. Executive Context

Phase 7 delivered a complete, verified **Consortium Blockchain Governance and Post-Quantum Cryptography Engine**, including:
1. Four-organization consortium topology with SmartBFT ordering simulation.
2. Go-based Hyperledger Fabric governance chaincode.
3. RFC 8785 JSON canonicalization and dual-signing (ECDSA P-256 + NIST FIPS 204 ML-DSA-65).
4. Independent two-person review approvals and monotonic rollback safety.
5. Transactional SQLite outbox relay and ledger outage handling.
6. Complete 8-workflow GitHub Actions CI/CD suite.

Phase 8 is responsible for **Production Hardening, Multi-Cloud Deployment, and Live Rural ISP Pilot Deployment**.

---

## 2. Handoff Interfaces & Artifact Contracts

### 2.1 Release Manifest & Model Pipeline Interfaces
Phase 8 can ingest candidate models from `artifacts/candidate-models/` and verify dual signatures using `DualSigner.verify_manifest()`:
```python
from fcs_governance.crypto.dual_signer import DualSigner
from fcs_governance.contracts.manifest import DualSignedReleaseManifest

# Phase 8 verifier verifies both conventional and post-quantum signatures
is_valid = DualSigner.verify_manifest(
    manifest=signed_manifest,
    expected_artifact_digest=artifact_sha384,
    trusted_ecdsa_key_hex=pinned_ecdsa_key,
    trusted_mldsa_key_hex=pinned_mldsa_key,
)
```

### 2.2 Fabric Gateway & Production Blockchain Handoff
Phase 7 provides:
- Chaincode source in `services/chaincode/governance/governance.go`.
- SmartBFT cluster definition in `services/governance/src/fcs_governance/fabric/topology.py`.
- Outbox event relay pattern ready for PostgreSQL migration in production.

---

## 3. Phase 8 Engineering Responsibilities

| Dimension | Phase 7 Delivered Baseline | Phase 8 Responsibility |
| :--- | :--- | :--- |
| **Blockchain Network** | Local SmartBFT simulation & Go chaincode unit tests. | Provision multi-host Kubernetes/Docker Fabric network across ISP tenant cloud accounts. |
| **Key Storage** | Software ephemeral keys in memory/trust store. | Integrate PKCS#11 / HSM adapters for production air-gapped private keys. |
| **Persistence** | Embedded SQLite outbox & ledger. | Migrate to distributed PostgreSQL with replication. |
| **Pilot Deployment** | Simulated 7-ISP partitions and local mock gateway. | Connect real live telemetry exporters from participating rural ISPs. |
| **Safety Invariant** | Permanent Manual Response (`network_action_executed = False`). | Maintain strict Manual Response Center SOC workflow during live pilot. |

---

## 4. Architectural Invariants for Phase 8

1. **Zero Automated Network Mitigation**: Phase 8 must NOT enable automatic firewall reconfiguration without SOC analyst manual confirmation.
2. **Zero-Cost Development Baseline**: All CI/CD and routine tests must remain 100% free on GitHub-hosted standard runners.
3. **Decoupled Detection Path**: Threat detection inference must never wait on synchronous blockchain network calls.
