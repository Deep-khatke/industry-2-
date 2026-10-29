# Federated Cyber Shield (FCS) v1.2 — Development Setup Guide

## 1. Prerequisites

- Python 3.11, 3.12, or 3.13
- Node.js 18+ or 20+ (with npm)
- Git
- OpenSSL (built into modern Windows/Linux/macOS)
- OpenTofu (optional for IaC verification)

---

## 2. Zero-Cost Local Installation

```bash
# 1. Clone repository (if not already local)
git clone https://github.com/Deep-khatke/industry-2-.git
cd "industry 2"

# 2. Install Python workspace packages in editable mode
python -m pip install -e packages/contracts
python -m pip install -e services/telemetry_validation
python -m pip install -e services/dataset_pipeline
python -m pip install -e services/ml_training
python -m pip install -e services/api
python -m pip install -e services/federated-learning
python -m pip install -e services/governance
python -m pip install -e services/pilot-management
python -m pip install -e . --no-deps

# 3. Install frontend dependencies
cd apps/security-dashboard
npm install
cd ../..
```

---

## 3. Running the Test Suite

```bash
# Run full monorepo regression suite (360 tests)
python -m pytest tests/

# Run Phase 11 specific hardening tests
python -m pytest tests/phase11/ -v
```

---

## 4. Launching the Services Locally

In Terminal 1 (FastAPI backend):
```bash
uvicorn services.api.src.fcs_api.app:app --host 127.0.0.1 --port 8000 --reload
```

In Terminal 2 (Security Dashboard):
```bash
cd apps/security-dashboard
npm run dev
```

Visit `http://localhost:5173` to explore the live security operations dashboard.
