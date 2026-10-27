# GitHub Repository Setup & Synchronization Runbook
**Federated Cyber Shield (FCS) — Phase 7: Consortium Blockchain, Post-Quantum Cryptography & Governance**
*Repository: https://github.com/Deep-khatke/industry-2- | Zero-Cost Invariant: ₹0 / $0*

---

## 1. Remote Repository Discovery & State

The official central version-control and CI/CD repository for Federated Cyber Shield is:
- **Repository URL**: `https://github.com/Deep-khatke/industry-2-`
- **Git Remote**: `https://github.com/Deep-khatke/industry-2-.git`
- **Owner**: `Deep-khatke`
- **Repository Name**: `industry-2-`

### Remote Discovery Findings
During initial inspection, `git ls-remote https://github.com/Deep-khatke/industry-2-.git` returned exit code 0 with an empty branch manifest, confirming the repository was newly created and unpopulated.

---

## 2. Safe Baseline Synchronization Sequence

To preserve the complete multi-phase lineage (Phase 1 Cloud Foundation, Phase 2 Datasets, Phase 3 ML Models, Phase 4 SOC Operations, Phase 5 FCS-HMD, and Phase 6 Federated Learning), synchronization was executed as follows:

```bash
# 1. Verify and configure git remote
git remote add origin https://github.com/Deep-khatke/industry-2-.git

# 2. Stage pristine Phase 1-6 source code (with .gitignore ignoring large parquet datasets and binaries)
git add .

# 3. Create foundational baseline commit on main
git commit -m "feat: complete Phases 1-6 foundation, datasets, detection, and federated learning"

# 4. Push main baseline to remote origin
git push -u origin main

# 5. Create dedicated development branch for Phase 7
git checkout -b feature/phase7-consortium-governance
```

---

## 3. Data Protection Invariants in Source Control

The repository `.gitignore` strictly protects against accidental exposure of sensitive telemetry, private keys, or heavy binary caches:
- **Zero Raw Data Committed**: `data/raw/`, `data/processed/*.parquet`, `data/staging/` are strictly ignored. Only small deterministic synthetic fixtures in `data/synthetic-fixtures/` are allowed.
- **Zero Private Keys Committed**: `*.pem`, `*.key`, `*.pfx`, `*.priv` are ignored.
- **Zero Local Databases Committed**: `*.sqlite`, `*.db`, `*.db-wal` are ignored.
- **No Node Modules**: `node_modules/`, `dist/` are ignored.
- **No Go Build Artifacts**: `bin/`, `*.exe`, `*.test` are ignored.
