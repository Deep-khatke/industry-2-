# Phase 8 GitHub Actions CI/CD Pipeline Specification

## 1. CI/CD Architecture & Zero-Cost Guardrails
The GitHub Actions CI/CD pipeline for Federated Cyber Shield (FCS v1.2) executes on repository `https://github.com/Deep-khatke/industry-2-` on branch `feature/phase8-integration-reliability`.
In strict compliance with the project's ₹0 budget and DevSecOps policies:
- **Standard Free Runners Only:** All jobs specify `runs-on: ubuntu-latest`. Larger or GPU-backed runners are prohibited.
- **Least Privilege Tokens:** Default `permissions: contents: read` across all workflow definitions.
- **Concurrency Management:** All jobs specify concurrency groups with `cancel-in-progress: true` to prevent resource waste.
- **Timeout Caps:** Hard timeouts of 10–15 minutes enforce bounded execution.
- **Pinned Commit SHAs:** External actions are pinned to immutable commit SHAs (e.g. `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683`).
- **No Production Deployments / Firewall Execution:** No workflow possesses cloud credentials or executes live network modifications.

## 2. Phase 8 Workflows Summary

| Workflow File | Purpose / Trigger | Stages Executed | Free Runner | Execution Timeout |
|---|---|---|---|---|
| `phase8-contract-validation.yml` | Validates all 20 cross-component contracts upon push/PR | Contract Matrix, Spec Integrity | `ubuntu-latest` | 10 mins |
| `phase8-system-integration.yml` | Verifies end-to-end data flow and 35-step demonstration | Ingest -> Inference -> Incident -> Manual Action | `ubuntu-latest` | 15 mins |
| `phase8-security-tests.yml` | Verifies multi-tenant isolation, IDOR prevention, and DP accounting | Adversarial Suite, Dual Signatures, Privacy | `ubuntu-latest` | 10 mins |
| `phase8-resilience-smoke.yml` | Executes fault matrix F01–F30 and backup restoration | Bounded Fault Injection, SQLite Backup/Restore | `ubuntu-latest` | 15 mins |
| `phase8-performance-smoke.yml`| Executes performance profiles P0–P4 and validates SLA | Nominal 1,400 flows/s, Burst, Latency Targets | `ubuntu-latest` | 10 mins |
| `phase8-release-readiness.yml`| Audits Release Gates G01–G15 and verifies ₹0 / Manual invariants | Gates Audit, Invariant Assertion, Status Emit | `ubuntu-latest` | 15 mins |

## 3. Pre-Existing Workflows Retained
Existing Phase 1–7 workflows remain preserved to maintain continuous verification of:
- `01-core-ci.yml`: Core Python contract tests
- `02-frontend-ci.yml`: Security Dashboard TypeScript/Vite tests
- `03-fabric-chaincode-ci.yml`: Go chaincode compilation and tests
- `04-cryptography-ci.yml`: PQC ML-DSA-65 and ECDSA cryptographic tests
- `05-security-ci.yml`: Dependency vulnerability scanning and secret detection
- `07-governance-release-validation.yml`: Governance manifest verification
- `08-phase7-verification.yml`: Phase 7 audit gates

## 4. Automation Safety Invariants
1. **Never Automatically Promote Models:** Training completion does not trigger model promotion into production.
2. **Never Automatically Enable AUTO Mode:** Response policies cannot be transitioned from MANUAL to AUTOMATIC by any CI job.
3. **Never Committ Sensitive Artifacts:** Audit logs and evidence bundles strip raw subscriber IPs and private keys.
