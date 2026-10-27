# FCS-PFL — Architecture & System Design
**Federated Cyber Shield (FCS) — Phase 6: Privacy-Preserving Federated Learning Engine**
*Architecture Version: 1.2.0 | Status: VERIFIED | Budget: ₹0 / $0*

---

## 1. System Overview

The **Federated Cyber Shield Privacy-Preserving Federated Learning Engine (FCS-PFL)** is the distributed machine learning subsystem of Federated Cyber Shield. It coordinates multi-tenant threat detection model training across seven simulated ISP participants (`isp_01` through `isp_07`) without centralizing raw network flow records, private labels, or plaintext gradient updates.

FCS-PFL addresses the fundamental tension in collaborative cyber defense:
1. **Collaborative Intelligence**: Cyber threats target multiple ISPs simultaneously. Pooling detection capabilities across providers enables early detection of coordinated botnets, scanning campaigns, and distributed denial-of-service (DDoS) infrastructure.
2. **Confidentiality & Privacy**: Telemetry records contain subscriber IPs, communication graphs, payload metadata, and competitive operational insights. Data regulations (GDPR, Telecom regulations) strictly forbid transferring raw network logs across administrative boundaries.

FCS-PFL resolves this by combining **Differential Privacy (DP-SGD)** at the tenant training boundary with **Cryptographic Secure Aggregation (Flower SecAgg+)** at the coordinator boundary.

```
PHASE 2 VERIFIED DATASETS
            │
            ▼
 SEVEN ISP DATA PARTITIONS (iid / moderate_non_iid / strong_non_iid)
            │
 ┌──────────┴──────────┬───────────┬───────────┬───────────┬───────────┐
 ▼                     ▼           ▼           ▼           ▼           ▼
ISP 1                ISP 2       ISP 3       ISP 4       ISP 5       ISP 6/7
 │                     │           │           │           │           │
 ▼                     ▼           ▼           ▼           ▼           ▼
LOCAL PYTORCH        LOCAL       LOCAL       LOCAL       LOCAL       LOCAL
TRAINING (MLP)       TRAIN       TRAIN       TRAIN       TRAIN       TRAIN
 │                     │           │           │           │           │
 ▼                     ▼           ▼           ▼           ▼           ▼
OPACUS DP-SGD        OPACUS      OPACUS      OPACUS      OPACUS      OPACUS
(Gradient Clip/Noise)  │           │           │           │           │
 │                     │           │           │           │           │
 ▼                     ▼           ▼           ▼           ▼           ▼
PRIVACY POLICY       POLICY      POLICY      POLICY      POLICY      POLICY
(SQLite Accountant)    │           │           │           │           │
 └──────────┬──────────┴───────────┼───────────┴───────────┴───────────┘
            ▼
 SECAGG+ CLIENT MASKING PROTOCOL (Pairwise Diffie-Hellman + Shamir Secret Sharing)
            │
            ▼
 FLOWER SUPERLINK SECAGG+ WORKFLOW (k = 5 / 7 Threshold)
            │
            ▼
 VALID AGGREGATED MODEL (Global FedAvg)
            │
            ▼
 CANDIDATE MODEL EVALUATION (Fairness & Holdout Gate)
            │
            ▼
 MODEL CANDIDATE REGISTRY (artifacts/candidate-models/)
            │
            ▼
 INTEGRITY AND APPROVAL GATE (Manual Response Control)
            │
            ▼
 FCS-HMD GENERAL DETECTOR (Hierarchical Multi-Model Engine)
            │
            ▼
 SECURITY DASHBOARD & SOC WORKFLOW (Manual Approval Invariant)
```

---

## 2. Process Boundaries & Components

FCS-PFL enforces clear process boundaries to prevent cross-tenant contamination and coordinator overreach:

### 2.1 Logical Participants (`isp_01` .. `isp_07`)
Each participant runs in an isolated tenant execution boundary:
- **TenantPartitionLoader**: Strictly reads only its assigned tenant partition (`data/processed/partitions/<profile>/<tenant_id>.parquet`). Checksum and record count verification are enforced before batch extraction.
- **Local Model**: Maintains an isolated instance of `TabularMLPNet` initialized with identical architectural hyper-parameters.
- **DPPrivacyEngine**: Opacus-backed per-example gradient clipping ($C = 1.0$) and calibrated Gaussian noise addition ($\sigma = 1.0$).
- **PrivacyAccountant**: An embedded SQLite ledger tracking cumulative privacy expenditure ($\epsilon \le 10.0, \delta = 10^{-5}$) per tenant, resilient to application crashes and restarts.
- **ParticipantAdmissionValidator**: Evaluates incoming `RoundManifest` instances against approved coordinator identities, code digests, schema digests, nonces, and sequence numbers.

### 2.2 Central Coordinator (Flower Superlink / ServerApp)
The coordinator manages round orchestration and aggregation:
- **Round Governance**: Issues versioned `RoundManifest` contracts signed by `fcs_dev_coordinator_signed`.
- **Flower SecAggPlusWorkflow**: Executes pairwise Diffie-Hellman key agreement, Shamir secret sharing of private blinding masks, and masked gradient aggregation.
- **Aggregation Strategy (`FCSFedAvgStrategy`)**: Enforces minimum contribution threshold ($k \ge 5$), sample or equal-client weighting, and sanity checks (NaN/Inf rejection).
- **Zero Plaintext Invariant**: The coordinator never receives raw feature vectors, private labels, or individual unmasked model parameters during protected rounds.

### 2.3 Model Registry & FCS-HMD Promotion
Aggregated weights undergo a strict four-state candidate lifecycle:
`TRAINED` $\rightarrow$ `VALIDATED` $\rightarrow$ `APPROVED` $\rightarrow$ `ACTIVE`
- Registered candidates reside in `artifacts/candidate-models/<candidate_id>/`.
- Candidate models are strictly restricted to the **General Intrusion Detector** slot in the FCS-HMD hierarchical tree.
- Anomaly detectors (IsolationForest) and specialist models (DDoS, Port Scan, Botnet) remain tenant-local and are never aggregated or shared.

---

## 3. Trust Assumptions & Threat Boundary

| Component | Trust Level | Boundary Enforcements |
| :--- | :--- | :--- |
| **Simulated ISPs** | Mutually Untrusted | Logical isolation, dedicated partition files, independent SQLite privacy ledgers. |
| **Central Coordinator** | Honest-but-Curious | Sees only masked aggregate sums $\sum x_i + \text{blinding}$, never individual tenant updates $x_i$. |
| **Network Channel** | Authenticated Simulation | HMAC nonces, signature verification, message sequence replay protection. |
| **Detection Engine** | Critical Security Path | Training process cannot modify running detector weights without explicit administrator promotion. |

---

## 4. Key Invariants

1. **Strict Zero-Cost Guarantee**: ₹0 / $0 incurred. Runs entirely on local CPU using standard open-source tools (PyTorch, Flower, Opacus, SQLite).
2. **Manual Response Invariant**: `network_action_executed = False` is permanently enforced across all mitigations. Automatic mode is disabled.
3. **No Plaintext Fallback**: If fewer than $k=5$ participants complete unmasking in SecAgg+, the round aborts immediately. Plaintext FedAvg fallback is prohibited in protected mode.
4. **Tenant Isolation**: Anomaly models and specialist detectors remain 100% tenant-local.
