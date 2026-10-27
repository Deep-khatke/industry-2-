# Participant Admission & Round Governance
**Federated Cyber Shield (FCS) — Phase 6: Privacy-Preserving Federated Learning Engine**
*Architecture Version: 1.2.0 | Status: VERIFIED | Budget: ₹0 / $0*

---

## 1. Admission Control Objectives

In decentralized federated learning, malicious or misconfigured coordinators can compromise participant privacy or system integrity by:
1. Impersonating a trusted aggregator to collect sensitive model updates.
2. Replaying stale round manifests to force redundant computation or desynchronize states.
3. Substituting the base model architecture or feature schema to extract specific participant data.
4. Altering DP noise or clipping policies to degrade privacy guarantees.

To counter these threats, FCS-PFL implements a **Client-Side Admission Control Gate** (`ParticipantAdmissionValidator`) that executes prior to each training round.

---

## 2. RoundManifest Specification

Every federated round is defined by a cryptographically signed contract (`RoundManifest`):

```python
class RoundManifest(BaseModel):
    round_id: str                      # UUID4 round identifier
    training_job_id: str               # High-level training campaign ID
    cohort_identity: str               # Expected cohort group (e.g. "fcs_tier1_isps_v1")
    participant_ids: List[str]         # Explicit list of allowed participant IDs
    base_model_digest: str             # SHA-256 of the initial weights
    application_code_digest: str       # SHA-256 of the approved fcs_pfl codebase
    feature_schema_digest: str         # SHA-256 of locked 14-feature deployable schema
    dataset_population_policy: str     # Dataset isolation policy
    privacy_policy_version: str        # Minimum approved privacy policy (e.g. "v1.0")
    training_hyperparameters: Dict     # Epochs, batch size, learning rate
    aggregation_protocol: AggregationProtocol # SECAGG_PLUS or PLAINTEXT_FEDAVG
    reconstruction_threshold: int      # Minimum clients required (k = 5)
    nonce: str                         # Hexadecimal replay protection nonce
    manifest_sequence: int             # Monotonically increasing sequence number
    validity_interval_start: datetime  # Window opening timestamp
    validity_interval_end: datetime    # Window expiration timestamp
    coordinator_signature: str         # Coordinator authentication token
```

---

## 3. Client-Side Admission Verification Pipeline

Before participating in training, each client (`isp_01` through `isp_07`) runs `validate_admission()`:

```
           Incoming RoundManifest
                     │
                     ▼
       [1. Coordinator Identity Check]
         Matches 'fcs_dev_coordinator_signed'? ───(No)───► REJECT: UNAUTHORIZED_COORDINATOR
                     │ (Yes)
                     ▼
        [2. Cohort Membership Check]
         Client ID in participant_ids? ──────────(No)───► REJECT: CLIENT_NOT_IN_COHORT
                     │ (Yes)
                     ▼
         [3. Temporal Validity Check]
         Within [start, end] window? ────────────(No)───► REJECT: MANIFEST_EXPIRED
                     │ (Yes)
                     ▼
         [4. Sequence Number Check]
         seq > last_seen_sequence? ──────────────(No)───► REJECT: STALE_MANIFEST_SEQUENCE
                     │ (Yes)
                     ▼
        [5. Replay Nonce Cache Check]
         nonce in recent_nonces? ────────────────(Yes)──► REJECT: REPLAY_ATTACK_DETECTED
                     │ (No)
                     ▼
       [6. Feature Schema Digest Check]
         Matches local locked 14-schema? ────────(No)───► REJECT: SCHEMA_MISMATCH
                     │ (Yes)
                     ▼
         [7. Privacy Budget Check]
         Available epsilon >= cost? ─────────────(No)───► REJECT: PRIVACY_BUDGET_EXHAUSTED
                     │ (Yes)
                     ▼
              ADMISSION APPROVED
```

---

## 4. Attack Mitigations & Test Verification

| Attack Vector | Mechanism Tested | Test File & Result |
| :--- | :--- | :--- |
| **Fake Coordinator** | Coordinator signature check rejects `fake_coordinator` | `test_rejection_of_unauthorized_coordinator` — **PASSED** |
| **Cohort Exclusion** | Client rejects manifest if its ID is omitted from `participant_ids` | `test_cohort_membership_enforcement` — **PASSED** |
| **Replay Attack** | Duplicate nonce in window is identified and blocked | `test_replay_attack_rejected` — **PASSED** |
| **Stale Sequence** | Out-of-order or duplicate sequence numbers are dropped | `test_sequence_ordering` — **PASSED** |
| **Schema Tampering** | Manipulated feature column digests abort admission | `test_schema_digest_mismatch_rejection` — **PASSED** |
| **Budget Exhaustion** | Epsilon check fails if cumulative spend $\ge 10.0$ | `test_exhausted_budget_blocks_export` — **PASSED** |

---

## 5. Audit Logging

Every admission decision (approval or rejection) is permanently logged to `artifacts/federation/manifests/admission_audit.jsonl` with timestamp, client ID, round ID, and specific violation codes.
