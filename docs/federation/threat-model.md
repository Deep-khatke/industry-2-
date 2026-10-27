# Security Threat Model & Risk Analysis
**Federated Cyber Shield (FCS) — Phase 6: Privacy-Preserving Federated Learning Engine**
*Architecture Version: 1.2.0 | Status: VERIFIED | Budget: ₹0 / $0*

---

## 1. System Scope & Adversary Capabilities

FCS-PFL operates in an adversarial environment where participating ISPs and the central coordinator may have competing commercial incentives, compromised nodes, or insider threats.

### 1.1 Threat Actors & Capabilities
1. **Honest-but-Curious Coordinator**: Follows protocol execution but attempts to reconstruct private network flows, subscriber identities, or tenant-specific models from received protocol messages.
2. **Malicious / Compromised Participant (Byzantine Client)**: Transmits poisoned gradients, manipulated manifests, or inverted labels to degrade global intrusion detection accuracy or install backdoors.
3. **Network Eavesdropper**: Monitors network traffic between ISPs and the Superlink coordinator.
4. **Rogue Operator / Insider**: Attempts to bypass Manual Response gates, promote unvetted models, or reset privacy budgets.

---

## 2. Threat Matrix & Countermeasure Mapping

| Threat ID | Threat Description | Attack Vector | Implemented Countermeasure | Residual Risk / Limitation |
| :--- | :--- | :--- | :--- | :--- |
| **TH-01** | **Coordinator Impersonation** | Rogue server solicits model weights from ISPs | `ParticipantAdmissionValidator` validates coordinator signature (`fcs_dev_coordinator_signed`) and public key. | In Phase 6 simulation, dev signature token is used; Phase 7 consortium PKI required for production. |
| **TH-02** | **Replay Attack** | Replaying old `RoundManifest` to stall training | Nonce caching and strictly monotonic `manifest_sequence` verification. | Nonce cache size is bounded to 1,000 nonces in memory. |
| **TH-03** | **Gradient Inversion / Snooping** | Extracting raw IP flows from individual model gradients | **Flower SecAgg+**: Pairwise Diffie-Hellman masks blind individual updates; coordinator only sees $\sum x_i$. | If $\ge 5$ of 7 participants collude, remaining 2 could theoretically be unmasked. |
| **TH-04** | **Membership Inference Attack** | White-box extraction of training samples from global model | **Opacus DP-SGD**: Per-example gradient clipping ($C=1.0$) and calibrated Gaussian noise ($\sigma=1.0$). | Record-level DP bounds individual flow inference, but does not provide subscriber-level DP. |
| **TH-05** | **Cross-Tenant Data Tampering** | Client attempts to read another ISP's parquet partition | `TenantPartitionLoader` enforces strict file path resolution and SHA-256 partition manifest validation. | Operating system permissions in multi-tenant environments must back this boundary. |
| **TH-06** | **Model Poisoning / Backdoors** | Malicious ISP sends corrupted updates to degrade detection | Candidate validation gate tests global holdout PR-AUC and per-tenant validation fairness. | **Critical Caveat**: SecAgg+ prevents the coordinator from inspecting individual updates! Poison detection is aggregate-only. |
| **TH-07** | **Unauthorized Model Promotion** | Training coordinator automatically replaces active detector | Candidate models are written to `artifacts/candidate-models/` in `TRAINED` state; activation requires manual approval. | Operational staff with local filesystem access could manually edit JSON configs. |
| **TH-08** | **Privacy Budget Reset** | Operator restarts training to bypass epsilon ceilings | SQLite `PrivacyAccountant` stores durable records in ACID database with monotonic increments. | Direct physical manipulation of the SQLite file would require root filesystem protection. |

---

## 3. The Fundamental SecAgg+ vs. Byzantine Defense Trade-off

> [!WARNING]
> **Cryptographic Masking Prevents Individual Poisoning Detection**:
> A critical insight of Phase 6 engineering: Because SecAgg+ blinds individual updates $x_u$, the coordinator receives **zero visibility** into whether any individual participant provided malicious, poisoned, or random gradients.
>
> Therefore, claims that a system provides both "complete secure aggregation" and "individual gradient anomaly detection" are mathematically contradictory. FCS Architecture v1.2 addresses this by:
> 1. Strict participant identity admission prior to training.
> 2. Aggregate post-training evaluation on independent holdout datasets.
> 3. Mandatory manual promotion gates prior to FCS-HMD deployment.

---

## 4. Manual Response Invariant Preservation

In all threat scenarios, the core architectural safety invariant holds:
- **`network_action_executed = False` is permanently enforced.**
- No model output, candidate promotion, or federated training failure can trigger automated firewall, BGP, or router reconfiguration. All responses require SOC analyst manual confirmation.
