# Failure Handling & Crash Recovery
**Federated Cyber Shield (FCS) — Phase 6: Privacy-Preserving Federated Learning Engine**
*Architecture Version: 1.2.0 | Status: VERIFIED | Budget: ₹0 / $0*

---

## 1. Round State Machine

Federated training rounds follow a formal 14-state machine (`RoundStateMachine` in `fcs_pfl/orchestration/state_machine.py`) ensuring auditable transitions and deterministic failure modes:

```
                      [ CREATED ]
                           │
                           ▼
                     [ VALIDATING ]
                           │
                           ▼
                     [ ADMITTING ]
                           │
                           ▼
                        [ SETUP ]
                           │
                           ▼
                     [ KEY_SHARING ]
                           │
                           ▼
                    [ LOCAL_TRAINING ]
                           │
                           ▼
                   [ MASKED_COLLECTION ]
                           │
                           ▼
                      [ UNMASKING ]
                     /            \
       (k >= 5 reached)          (k < 5 abort)
            /                              \
           ▼                                ▼
[ AGGREGATE_VALIDATION ]               [ ABORTED ]
           │
           ▼
     [ EVALUATING ]
           │
           ▼
   [ CANDIDATE_READY ]
```

Terminal states: `CANDIDATE_READY`, `ABORTED`, `FAILED`, `RECOVERY_REQUIRED`.

---

## 2. Failure Scenarios & Recovery Procedures

### 2.1 Client Dropouts during Training
- **Dropouts at Stage 1 / Stage 2**: If a client drops before completing key sharing, the coordinator recalculates the active cohort $U_1$. If $|U_1| < 5$, the round aborts.
- **Dropouts at Stage 3 / Stage 4**: If up to 2 clients drop out during local training or masked collection, surviving clients provide Shamir shares of the dropped clients' pairwise keys $s_{u,v}$. The coordinator eliminates their pairwise masks and reconstructs the aggregate sum of the 5 or 6 surviving clients.
- **Excessive Dropouts ($\ge 3$ dropped)**: Surviving clients $< 5$. The coordinator enters `ABORTED`. **No plaintext fallback is permitted.**

### 2.2 Coordinator Crash during Round Execution
- If the coordinator process crashes midway through a round, ephemeral Diffie-Hellman keys and unmasking states are permanently lost.
- Upon restart, the `RecoveryManager` (`fcs_pfl/checkpoints/recovery.py`):
  1. Inspects the last checkpoint in `artifacts/federation/checkpoints/`.
  2. Marks any incomplete round as `FAILED` or `ABORTED`.
  3. Reconciles `PrivacyAccountant` receipts to ensure reserved budgets are closed.
  4. Generates a fresh round ID and fresh nonces for the subsequent attempt. Stale protocol sessions are **never resumed**.

### 2.3 Checkpoint Corruption
- Checkpoints are saved as `.pt` state dicts accompanied by SHA-256 `.json` manifests.
- If a checkpoint hash fails verification or contains mismatched tensor dimensions, the `RecoveryManager` rejects the file, enters `RECOVERY_REQUIRED`, and prevents any promotion attempt.

---

## 3. Detection Continuity Invariant

> [!IMPORTANT]
> **Active Detection Pipeline Isolation**:
> The federated training engine runs as an asynchronous, decoupled subsystem. If a training round aborts, crashes, or is terminated due to budget exhaustion:
> 1. The currently running **FCS-HMD detection engine** continues processing live network flows with 100% availability.
> 2. The active general detector weights (`artifacts/candidate-models/` or baseline LightGBM) remain untouched.
> 3. Incidents continue to stream to the SOC Security Dashboard without disruption.
