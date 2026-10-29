# Federated Cyber Shield (FCS) v1.2 — DevSecOps CI/CD Architecture

## 1. Zero-Cost GitHub Actions Pipeline Design

FCS implements an automated DevSecOps pipeline utilizing free standard `ubuntu-latest` runners without reliance on paid compute, managed secrets stores, or billable third-party integrations.

```mermaid
flowchart TD
    GitPush[Git Push / PR to main] --> MatrixCI[1. Core CI & Matrix Regression]
    GitPush --> SecAudit[2. Security Audit & Zero-Cost Guardrails]
    GitPush --> SBOMGen[3. SBOM Generation & Verification]
    GitPush --> ContractTest[4. Contract Tests & Schema Conformance]
    GitPush --> IntegrationCI[5. End-to-End System Integration]
    GitPush --> RecoverySmoke[6. Disaster Recovery & Fault Smoke]
    GitPush --> ReleaseVal[7. Release Candidate Validation & Signing]

    MatrixCI & SecAudit & SBOMGen & ContractTest & IntegrationCI & RecoverySmoke & ReleaseVal --> FinalGate[8. Final Release Verification (G01-G15)]
    FinalGate --> ReleaseVerdict[DEVELOPMENT_RELEASE_VERIFIED]
```

---

## 2. Workflow Matrix & Job Specifications

| Workflow File | Trigger Events | Core Tasks Executed | Standard Enforced |
|---|---|---|---|
| `phase11-core-ci.yml` | Push/PR | Python 3.11/3.12 regression suite + Vite dashboard build | 100% test pass rate |
| `phase11-security-audit.yml` | Push/PR | Zero-cost scanner + dependency audit + RBAC security tests | 0 violations, clean dependencies |
| `phase11-sbom.yml` | Push/PR | Generate CycloneDX 1.5 & SPDX 2.3 SBOMs | NTIA minimum elements |
| `phase11-contract-tests.yml` | Push/PR | System contracts & API schema conformance | 100% contract compliance |
| `phase11-integration.yml` | Push/PR | Multi-tenant incident flow & scenario replay | End-to-end pipeline integrity |
| `phase11-recovery-smoke.yml` | Push/PR | SQLite online backup & sandboxed restore validation | Zero data loss, RTO < 60s |
| `phase11-release-validation.yml` | Push/PR | Dual manifest signing (ECDSA + ML-DSA-65) & SLO benchmarks | Verified cryptographic signatures |
| `phase11-final-verification.yml` | Push/PR | Unified verification script (`scripts/verify_phase11.py`) | Architecture gates G01–G15 audit |

---

## 3. Least-Privilege & Hardening Policies

- **Token Permissions**: All workflows explicitly declare `permissions: contents: read`.
- **Concurrency Control**: Redundant builds on the same branch are automatically cancelled using `cancel-in-progress: true`.
- **Zero Cloud Charges**: No workflow triggers external cloud APIs, spins up billable runners, or creates storage buckets.
