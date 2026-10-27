# Phase 7 Handoff Specification
**Federated Cyber Shield (FCS) — Phase 6 to Phase 7 Transition**
*Consortium Governance, Blockchain Audit Ledger, and Post-Quantum Model Signing*

---

## 1. Executive Context

Phase 6 established a fully functioning, verified **Privacy-Preserving Federated Learning Engine (FCS-PFL)** utilizing Flower SecAgg+, Opacus DP-SGD, and persistent SQLite privacy accounting across seven simulated ISP participants.

Phase 7 is responsible for **Consortium Governance, Blockchain Audit, and Post-Quantum Cryptographic Model Signing**.

To ensure clean decoupling, Phase 6 exposes stable, versioned schemas and interfaces so that Phase 7 can layer decentralized governance and quantum-resilient signatures over candidate models **without modifying the internal federated training and aggregation algorithms.**

---

## 2. Stable Handoff Interfaces & Contracts

### 2.1 Candidate Manifest Contract (`CandidateManifest`)
Located in `services/federated-learning/src/fcs_pfl/contracts/manifests.py`:

```python
class CandidateManifest(BaseModel):
    candidate_id: str                      # Unique UUID for the candidate model
    model_family: str                      # "tabular_mlp"
    architecture_version: str              # "1.2.0"
    base_model_digest: str                 # SHA-256 of initial weights
    candidate_weight_digest: str           # SHA-256 of aggregated weights
    feature_schema_digest: str             # SHA-256 of 14 locked deployable features
    privacy_policy_digest: str             # SHA-256 of privacy parameters used
    privacy_receipt_references: List[str]  # List of UUID receipts from SQLite ledger
    participating_clients: List[str]       # e.g. ["isp_01", ..., "isp_07"]
    aggregation_protocol: AggregationProtocol # "SECAGG_PLUS"
    status: CandidateStatus                # TRAINED, VALIDATED, APPROVED, ACTIVE, REJECTED
    holdout_evaluation_metrics: Dict       # PR-AUC, F1, Accuracy, FPR
    tenant_fairness_metrics: Dict          # Worst-client F1, variance
    created_at: datetime
    
    # Phase 7 Extension Slots
    consortium_release_request_id: Optional[str] = None
    pq_signature_dilithium: Optional[str] = None
    pq_signature_falcon: Optional[str] = None
    blockchain_tx_hash: Optional[str] = None
    consortium_approval_signatures: Dict[str, str] = Field(default_factory=dict)
    revocation_status: Optional[str] = None
    rollback_target_candidate_id: Optional[str] = None
```

### 2.2 Round Manifest Contract (`RoundManifest`)
Phase 7 will anchor `RoundManifest` instances onto the consortium blockchain prior to training round initiation to provide tamper-proof provenance for training jobs.

---

## 3. Candidate Model Artifact Structure

Phase 6 exports all candidate models to `artifacts/candidate-models/<candidate_id>/`:
```
artifacts/candidate-models/candidate_exp_e6_06/
├── model.pt                 # PyTorch state dict (3,362 float32 parameters)
├── model.json               # Serialized architecture and parameter list
├── model_manifest.json      # Integrity hashes, parameter count, input shape
└── candidate_manifest.json  # Full CandidateManifest contract with evaluation metrics
```

Phase 7 can ingest this directory directly, compute cryptographic digests, attach post-quantum signatures, and submit the release request to the consortium smart contract.

---

## 4. Phase 7 Integration Checklist & Responsibilities

| Subsystem | Phase 6 Delivered Baseline | Phase 7 Responsibility |
| :--- | :--- | :--- |
| **Model Signatures** | HMAC development signature (`fcs_dev_coordinator_signed`). | Implement CRYSTALS-Dilithium and Falcon post-quantum signature schemes. |
| **Audit Ledger** | Local JSONL files & SQLite `privacy_receipts`. | Anchor model digests, round receipts, and admission events to consortium blockchain. |
| **Consortium Governance** | Local admin role for model activation. | Multi-signature $M$-of-$N$ ISP consortium voting contract for model promotion. |
| **Revocation & Rollback** | `CandidateModelRegistry.rollback_to_model()`. | On-chain revocation alerts triggering immediate local fallback to pre-verified checkpoints. |
| **Detection Independence** | Decoupled FCS-HMD general detector adapter. | Ensure on-chain voting does not introduce latency or blocking into the live detection path. |

---

## 5. Architectural Invariants for Phase 7

1. **Zero-Cost Constraint**: Phase 7 must implement consortium testing on local free emulated blockchains (e.g. local Ethereum devnets or Anvil/Ganache/Substrate local nodes) with **₹0 / $0 spend**.
2. **Manual Response Safety**: Phase 7 blockchain contracts must **never** automate network mitigation execution. The `network_action_executed = False` invariant must be strictly preserved.
3. **Local Anomaly Model Isolation**: Anomaly models and specialist models must remain outside consortium visibility.
