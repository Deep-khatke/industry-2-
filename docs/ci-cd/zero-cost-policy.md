# Strict Zero-Cost Policy & Runner Resource Bounds
**Federated Cyber Shield (FCS) — Phase 7: Consortium Blockchain, Post-Quantum Cryptography & Governance**
*Total Allowed Budget: Strictly ₹0.00 / $0.00*

---

## 1. Absolute Prohibition of Paid Services

The development, testing, CI/CD, and demonstration of Phase 7 must incur zero financial cost. The following are strictly prohibited:
- Paid cloud infrastructure (AWS EC2, ECS, RDS, S3, KMS, CloudWatch).
- Paid blockchain platforms (Hyperledger Fabric managed cloud nodes, Infura, Alchemy, QuickNode).
- Paid hardware security modules (AWS CloudHSM, Google Cloud HSM, Azure Dedicated HSM).
- Paid code quality / security SaaS (Snyk, SonarQube Enterprise, Coveralls).
- Paid GitHub runner tiers (GitHub Actions Larger Runners, GPU Runners, M1 macOS Runners).
- Any promotional-credit or credit-card-backed cloud services with uncertain or automatic billing.

---

## 2. GitHub Actions Resource Bounds

All GitHub Actions workflows are strictly constrained to free-tier resources:

1. **Standard Runners Only**: Every job explicitly runs on `runs-on: ubuntu-latest` (2-core standard free runners).
2. **Explicit Timeouts**: Every job defines `timeout-minutes: 10` or `15` to prevent runaway processes from consuming monthly minute allowances.
3. **Redundant Job Cancellation**: Redundant CI runs on the same branch are automatically canceled (`cancel-in-progress: true`).
4. **No Full Training in CI**: Workflows do NOT execute full 7-client federated training or large dataset downloads (NF-UQ-NIDS-v2); deterministic synthetic fixtures are used for CI verification.
5. **Minimal Artifact Retention**: Log files and ephemeral test outputs specify minimal retention (1-3 days).

---

## 3. Financial Expenditure Audit

| Subsystem / Resource | Incurred Cost | Verification Status |
| :--- | :---: | :---: |
| Local Python Development (PyTorch, Opacus, dilithium-py) | ₹0.00 | **VERIFIED** |
| Local Hyperledger Fabric Chaincode (Go 1.22) | ₹0.00 | **VERIFIED** |
| Local SmartBFT Ledger Emulation (SQLite) | ₹0.00 | **VERIFIED** |
| React Security Dashboard (Vite / TypeScript) | ₹0.00 | **VERIFIED** |
| GitHub Actions Workflows (8 Free Ubuntu Workflows) | ₹0.00 | **VERIFIED** |
| **Total Phase 7 Expenditure** | **₹0.00 / $0.00** | **VERIFIED** |
