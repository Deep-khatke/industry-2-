# GitHub Actions CI/CD Architecture
**Federated Cyber Shield (FCS) — Phase 7: Consortium Blockchain, Post-Quantum Cryptography & Governance**
*Architecture Baseline: FCS Architecture v1.2 | Zero-Cost Invariant: ₹0 / $0*

---

## 1. System Mission & CI/CD Objectives

Federated Cyber Shield (FCS) operates under a mission-critical cybersecurity paradigm: providing decentralized threat detection for rural Internet Service Providers without incurring infrastructure costs or violating data protection regulations.

Continuous Integration and Continuous Delivery (CI/CD) in FCS enforces software supply chain integrity, multi-architecture verification, and cryptographic signing validity across every pull request and release candidate.

```
Developer Workspace (Google Antigravity)
                 │
                 ▼
Feature Branch: feature/phase7-consortium-governance
                 │
                 ▼
Pull Request / Push to GitHub (https://github.com/Deep-khatke/industry-2-)
                 │
  ┌──────────────┴───────────────────────────┬───────────────────────────┐
  ▼                                          ▼                           ▼
01-Core-CI (Python)                 02-Frontend-CI (React/TS)   03-Fabric-Chaincode-CI (Go)
(Lint, Typecheck, Unit)             (Vite, ESLint, TypeScript)  (Go Vet, Fabric Contracts)
  │                                          │                           │
  ├──────────────────────────────────────────┼───────────────────────────┤
  ▼                                          ▼                           ▼
04-Cryptography-CI                  05-Security-CI              06-Integration-CI
(RFC 8785, ECDSA, ML-DSA-65)        (Supply Chain, Secrets)     (End-to-End Governance)
  └──────────────────────────────────────────┬───────────────────────────┘
                                             │
                                             ▼
                        07-Governance-Release-Validation
                        (Canonical Manifest, SHA-384 Digest, Reviewers)
                                             │
                                             ▼
                             08-Phase7-Verification
                             (Release Gates G10 & G11 Audit)
                                             │
                                             ▼
                       Consortium Human & Multi-Org Governance
                       (Zero Automated Cloud Deployments to Paid AWS)
```

---

## 2. Workflows Inventory

The `.github/workflows/` directory contains 8 specialized, decoupled workflows:

| Workflow File | Name | Trigger Scope | Timeout | Execution Profile |
| :--- | :--- | :--- | :---: | :--- |
| `01-core-ci.yml` | 01-Core-CI | Push / PR to main/features | 10 min | Python 3.11, Ruff, Phase 1-6 Unit Tests |
| `02-frontend-ci.yml` | 02-Frontend-CI | Changes in `apps/security-dashboard/**` | 10 min | Node 20, Vite production bundle build |
| `03-fabric-chaincode-ci.yml` | 03-Fabric-Chaincode-CI | Changes in `services/chaincode/**` | 10 min | Go 1.22, Go vet, Fabric chaincode unit tests |
| `04-cryptography-ci.yml` | 04-Cryptography-CI | Push / PR | 10 min | RFC 8785, ECDSA P-256 (SHA-384), ML-DSA-65 |
| `05-security-ci.yml` | 05-Security-CI | Push / PR | 10 min | Secret scanning, supply-chain authorization |
| `06-integration-ci.yml` | 06-Integration-CI | Push / PR | 15 min | Outbox relay, ledger outage, FCS-HMD bridge |
| `07-governance-release-validation.yml` | 07-Governance-Release-Validation | Dispatch / PR on `artifacts/candidate-models/**` | 10 min | Release artifact validation (no auto-deploy) |
| `08-phase7-verification.yml` | 08-Phase7-Verification | Push to main / Manual dispatch | 15 min | Full gate audit (G10/G11 status generation) |

---

## 3. Strict Least-Privilege Security Rules

All workflows adhere to strict DevSecOps supply-chain principles:
1. **Read-Only Permissions**: Default `GITHUB_TOKEN` permissions are pinned to `contents: read`. No workflow possesses write or deployment permissions unless specifically declared and justified.
2. **Untrusted PR Protection**: Never use `pull_request_target` to execute untrusted code from forks.
3. **No Production Keys in CI**: Disposable development keys generated in memory are utilized exclusively during test execution. Production signing keys remain in offline HSMs.
4. **Concurrency Control**: Redundant workflow runs on the same branch are automatically canceled (`cancel-in-progress: true`) to preserve runner resources.
5. **No Paid Runners**: All workflows execute on standard free `ubuntu-latest` GitHub-hosted runners.
