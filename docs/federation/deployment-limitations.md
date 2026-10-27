# Deployment Limitations & Production Gap Analysis
**Federated Cyber Shield (FCS) — Phase 6: Privacy-Preserving Federated Learning Engine**
*Architecture Version: 1.2.0 | Status: VERIFIED | Budget: ₹0 / $0*

---

## 1. Executive Disclosure: Simulation vs. Production

> [!WARNING]
> **Simulation Boundary Notice**:
> Phase 6 executes in a local development environment under a strict **₹0 / $0 Zero-Cost Constraint**.
> While the 7 simulated ISP participants (`isp_01` through `isp_07`), the Flower SecAgg+ protocol, Opacus DP-SGD, and SQLite privacy accounting are mathematically and algorithmically genuine, **running 7 processes on a single host is not equivalent to a geographically distributed deployment across seven independent commercial telecommunications operators.**

---

## 2. Comparison: Phase 6 Development vs. Production Target

| Architectural Dimension | Phase 6 Implemented Reality | Production Commercial Target |
| :--- | :--- | :--- |
| **Participant Isolation** | Logical process isolation; independent parquet files in `data/processed/partitions/`. | Distinct AWS/GCP accounts, private tenant VPCs, strict network isolation. |
| **Network Communication** | In-process Python queues & HTTP loopback interfaces. | Authenticated mTLS channels over public internet with BGP-aware routing. |
| **Cryptographic Identity** | Development HMAC tokens (`fcs_dev_coordinator_signed`). | Hardware Security Module (HSM) backed PKI with X.509 tenant certificates. |
| **Privacy Ledger Storage** | Embedded SQLite database (`data/federation_privacy.db`). | Distributed, Byzantine-fault-tolerant database replicated across tenant nodes. |
| **Model Verification** | SHA-256 state dict hashes in local JSON manifests. | Post-Quantum signatures (CRYSTALS-Dilithium) anchored to Consortium Blockchain (Phase 7). |
| **Audit Trails** | Append-only local JSONL log files. | Immutable distributed ledger (Hyperledger Fabric / Ethereum rollups). |
| **Host Trust** | A malicious local root user could inspect process memory or SQLite files. | Confidential Computing (AMD SEV-SNP / Intel SGX) enclaves per participant. |

---

## 3. What Phase 6 Genuinely Proves

1. **Mathematical Soundness**:
   - The Flower SecAggPlus masking protocol operates correctly with $k=5/7$ threshold, cancels pairwise masks, bounds quantization error ($< 10^{-5}$), and reliably aborts when dropouts exceed threshold.
   - Opacus DP-SGD with `GroupNorm` computes per-example clipped gradients and tracks cumulative RDP privacy budgets without layer incompatibilities.
2. **Crash-Consistent Ledger Logic**:
   - The SQLite privacy state machine accurately tracks cumulative spend across restarts, enforces hard caps at $\epsilon = 10.0$, and blocks overspend attempts.
3. **Detection Architecture Decoupling**:
   - Federated model candidates can be registered, evaluated, and promoted into the FCS-HMD general detector slot without disrupting tenant-local anomaly models, specialists, or the SOC Manual Response workflow.

---

## 4. Roadmap to Production (Phase 7 & Beyond)

The deferred requirements will be addressed in subsequent architectural phases:
- **Phase 7 (Consortium Governance & Audit)**: Post-quantum model signing, decentralized consortium approval policies, and distributed ledger audit records.
- **Phase 8 (Production Deployment & Hardening)**: Multi-cloud Terraform/OpenTofu configurations, mTLS mesh (Envoy/Istio), and Confidential Computing enclave support.
