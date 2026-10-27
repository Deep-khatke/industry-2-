# Persistent Privacy Budget Accounting
**Federated Cyber Shield (FCS) — Phase 6: Privacy-Preserving Federated Learning Engine**
*Architecture Version: 1.2.0 | Status: VERIFIED | Budget: ₹0 / $0*

---

## 1. Accounting Architecture & Rationale

In differential privacy, privacy loss is strictly cumulative. Running $K$ successive training rounds on the same tenant dataset continuously consumes the overall privacy budget. Without durable, crash-consistent accounting, process restarts or network failures could allow an operator to reset the accountant counter and train indefinitely, completely eroding formal DP guarantees.

FCS-PFL implements a **Persistent Privacy Budget Engine** (`PrivacyAccountant` in `fcs_pfl/privacy/accountant.py`) backed by an embedded SQLite ledger.

---

## 2. Database Schema & Tables

The privacy engine maintains two primary relational tables in `data/federation_privacy.db`:

### 2.1 `tenant_privacy_state`
Tracks tenant-level cumulative limits and expenditures:
```sql
CREATE TABLE IF NOT EXISTS tenant_privacy_state (
    tenant_id TEXT PRIMARY KEY,
    privacy_policy_id TEXT NOT NULL,
    epsilon_ceiling REAL NOT NULL DEFAULT 10.0,
    delta_ceiling REAL NOT NULL DEFAULT 1e-5,
    cumulative_epsilon REAL NOT NULL DEFAULT 0.0,
    reserved_epsilon REAL NOT NULL DEFAULT 0.0,
    last_round_id TEXT,
    state_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 `privacy_receipts`
Durable receipts for every reservation and committed round:
```sql
CREATE TABLE IF NOT EXISTS privacy_receipts (
    receipt_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    round_id TEXT NOT NULL,
    epsilon_spent REAL NOT NULL,
    delta_spent REAL NOT NULL,
    noise_multiplier REAL NOT NULL,
    clipping_norm REAL NOT NULL,
    steps_executed INTEGER NOT NULL,
    status TEXT NOT NULL, -- RESERVED, COMMITTED, ABORTED
    receipt_digest TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(tenant_id) REFERENCES tenant_privacy_state(tenant_id)
);
```

---

## 3. Privacy Lifecycle & Crash Consistency

To guarantee ACID durability across failures, each training round executes a three-phase state machine:

```
[Idle Tenant State]
       │
       ▼
 1. RESERVE BUDGET
    - Checks: cumulative_epsilon + reserved_epsilon + requested_epsilon <= epsilon_ceiling
    - If valid: increments reserved_epsilon, writes receipt (status = 'RESERVED')
    - If exceeded: throws PrivacyBudgetExhaustedError, round blocks immediately.
       │
       ▼
 2. LOCAL TRAINING & OPACUS DP-SGD
    - Model computes per-example clipped and noised gradients.
    - True epsilon measured via Opacus RDP accountant.
       │
       ▼
 3. COMMIT SPEND (or ABORT)
    - If round succeeds:
        cumulative_epsilon += true_epsilon
        reserved_epsilon -= requested_epsilon
        receipt status updated to 'COMMITTED'
    - If round crashes or is aborted:
        reserved_epsilon -= requested_epsilon
        receipt status updated to 'ABORTED'
        NOTE: Cumulative budget is NOT refunded if data-dependent gradients were computed.
```

---

## 4. Key Security Invariants

1. **No Silent Resets**: Epsilon ceilings are bound permanently to the tenant ID. Restarting the Python process, rebooting the server, or starting a new training session never resets cumulative epsilon.
2. **Double-Spend Prevention**: Multiple concurrent training requests for the same tenant cannot double-spend uncommitted budget; reservations lock budget in atomic SQLite transactions.
3. **Conservative Failed-Round Accounting**: If a training round fails after gradients were computed, privacy loss has occurred locally. The spend is accounted for and never refunded.
4. **Hard Exhaustion Gate**: Once `cumulative_epsilon >= 10.0`, any further `reserve_budget()` call is rejected with `PRIVACY_BUDGET_EXHAUSTED`.

---

## 5. Security Gate G05 Verification

FCS Architecture v1.2 mandates Release Gate **G05 (Differential Privacy Accounting Verification)**:
- **Budget Reservation & Receipts**: Verified in `test_privacy_budget_reservation_and_commit`.
- **Cumulative Tracking across Restarts**: Verified in `test_privacy_accountant_persistence_across_restarts`.
- **Hard Spend Exhaustion**: Verified in `test_exhausted_budget_blocks_export` and experiment `E6-11`.
- **Crash Recovery**: Verified in `test_crash_consistency_recovery`.

**Status: G05 VERIFIED.**
