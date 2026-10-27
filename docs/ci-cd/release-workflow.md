# Controlled Continuous Delivery & Model Release Runbook
**Federated Cyber Shield (FCS) — Phase 7: Consortium Blockchain, Post-Quantum Cryptography & Governance**
*Architecture Baseline: FCS Architecture v1.2 | Zero-Cost Invariant: ₹0 / $0*

---

## 1. Controlled CD Philosophy

In FCS, Continuous Delivery **does not mean automated cloud deployments to production networks or automatic detector weight swaps**.

Continuous Delivery means:
1. Automated verification of model candidate artifacts and manifests.
2. Cryptographic validation of dual signatures and evaluation metrics.
3. Preparation of governed release evidence bundles.
4. Retention of immutable audit records.
5. Strict gating requiring explicit human and consortium multi-organization authorization prior to any tenant activation.

---

## 2. Release Candidate Lifecycle (The 12 Formal States)

```
[ CANDIDATE ] ───► [ UNDER_REVIEW ] ───► [ APPROVED ] ───► [ SIGNING_PENDING ]
      │                   │                    │                     │
      ▼                   ▼                    ▼                     ▼
 [ REJECTED ]        [ REJECTED ]         [ REJECTED ]          [ REJECTED ]
                                                                     │
                                                                     ▼
[ ELIGIBLE_FOR_ACTIVATION ] ◄─── [ LEDGER_COMMITTED ] ◄─── [ LEDGER_PENDING ] ◄─── [ SIGNED ]
      │                                       │
      ▼                                       ▼
  [ ACTIVE ] ───► [ ROLLED_BACK ]        [ REVOKED ]
      │
      ▼
 [ REVOKED ]
```

---

## 3. End-to-End Promotion & Activation Sequence

### Step 1: Candidate Ingestion
The candidate model is produced by Phase 6 federated learning in `artifacts/candidate-models/<candidate_id>/`.

### Step 2: Independent Reviewer Approvals
Reviewer A (Security Reviewer) and Reviewer B (Privacy/ML Reviewer) record independent approvals:
```bash
python tools/fcs_gov.py releases approve --release-id <id> --role REVIEWER_A --user alice_sec
python tools/fcs_gov.py releases approve --release-id <id> --role REVIEWER_B --user bob_privacy
```

### Step 3: Canonical Dual-Signing
The canonical manifest body (strictly $\le 4096$ bytes per RFC 8785) is dual-signed using ECDSA P-256 (SHA-384) and ML-DSA-65 (NIST FIPS 204):
```bash
python tools/fcs_gov.py releases sign --release-id <id> --sequence 1
```

### Step 4: Consortium Endorsement & Fabric Commit
Three out of the four consortium governing organizations (`Org1MSP`, `Org2MSP`, `Org3MSP`) endorse the transaction. The SmartBFT consensus orderers commit the release block to the ledger.

### Step 5: Tenant Activation
The tenant administrator authorizes local activation into the FCS-HMD general detector slot:
```bash
curl -X POST http://localhost:8000/v1/tenant-model/activate \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "isp_01", "tenant_admin_signature": "auth_token_sig"}'
```

### Step 6: Revocation or Monotonic Rollback
If performance drift or a vulnerability is identified, the model is revoked or rolled back to a prior verified release with a strictly higher manifest sequence number.
