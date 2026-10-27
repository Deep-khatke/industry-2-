# Branch Protection & Pull Request Governance Policy
**Federated Cyber Shield (FCS) — Phase 7: Consortium Blockchain, Post-Quantum Cryptography & Governance**
*Repository: https://github.com/Deep-khatke/industry-2- | Zero-Cost Invariant: ₹0 / $0*

---

## 1. Branch Strategy

FCS enforces a disciplined Git branching topology:
- **`main`**: The canonical, production-ready baseline. Direct pushes to `main` are strictly forbidden once initial bootstrapping is complete.
- **`feature/*`**: Feature branches for autonomous engineering phases (e.g. `feature/phase7-consortium-governance`).
- **`fix/*`**: Isolated hotfixes and defect remediation.

---

## 2. Recommended Branch Protection Rules for `main`

The repository owner (`Deep-khatke`) should configure the following branch protection settings under **Settings -> Branches -> Add classic branch protection rule** for `main`:

1. **Require a pull request before merging**:
   - Require approvals: Minimum **1 approval**.
   - Dismiss stale pull request approvals when new commits are pushed.
   - Require review from Code Owners where applicable.
2. **Require status checks to pass before merging**:
   - Require branches to be up to date before merging.
   - Mandatory required checks:
     - `01-Core-CI / Python Lint, Typecheck & Unit Tests`
     - `02-Frontend-CI / React TypeScript Build & Quality`
     - `03-Fabric-Chaincode-CI / Go Vet & Hyperledger Fabric Chaincode Tests`
     - `04-Cryptography-CI / RFC 8785, ECDSA P-256 & ML-DSA-65 Tests`
     - `05-Security-CI / Security Tests & Release Authorization Checks`
     - `06-Integration-CI / End-to-End Governance & Ledger Recovery Tests`
3. **Require conversation resolution before merging**:
   - All code review comments and discussions must be marked resolved.
4. **Do not allow bypassing the above settings**:
   - Enforce for administrators and automation bots alike.
5. **Block force pushes and branch deletions**:
   - Prevent `git push --force` and accidental branch removal on `main`.

---

## 3. Distinction: GitHub PR Approval vs. Model Governance Approval

> [!IMPORTANT]
> **Separation of Concerns**:
> A GitHub pull-request approval by a repository committer **only authorizes source code merging**.
> It **DOES NOT** authorize model activation into live intrusion detection.
>
> Model promotion requires the distinct Phase 7 Consortium Governance pipeline:
> - Reviewer A (Security Reviewer) formal approval.
> - Reviewer B (Privacy Reviewer) formal approval.
> - Dual-signed manifest (ECDSA P-256 + ML-DSA-65).
> - 3-of-4 Hyperledger Fabric consortium peer endorsements.
> - SmartBFT ledger commitment verification.
> - Tenant administrator explicit activation authorization.
