# Phase 6 Operational Runbook
**Federated Cyber Shield (FCS) — Phase 6: Privacy-Preserving Federated Learning Engine**
*Architecture Version: 1.2.0 | Status: VERIFIED | Budget: ₹0 / $0*

---

## 1. Quick Start & Prerequisites Check

Verify that the local environment meets all Phase 6 dependencies (PyTorch 2.x, Flower 1.42, Opacus 1.6, Polars, DuckDB):

```bash
# Run CLI prerequisite inspection
python tools/fcs_fl.py verify-prerequisites
```

Expected Output:
```
============================================================
FCS-PFL Prerequisites & System Inspection
============================================================
[+] PyTorch: 2.14.0+cu126 (CUDA Available: True)
[+] Flower: 1.42.0
[+] Opacus: 1.6.0
[+] Polars: 1.22.1
[+] DuckDB: 1.2.0
[+] Partitions Directory: data\processed\partitions
[+] Candidate Models Directory: artifacts\candidate-models
[+] Checkpoints Directory: artifacts\federation\checkpoints
[+] Status: ALL PREREQUISITES VERIFIED
```

---

## 2. CLI Command Reference (`tools/fcs_fl.py`)

### 2.1 System & Participant Inspection
```bash
# Display system overview and environment status
python tools/fcs_fl.py inspect

# List all 7 registered ISP participants and partition allocations
python tools/fcs_fl.py participants list

# Check cumulative privacy budget usage for all participants
python tools/fcs_fl.py privacy status
```

### 2.2 Protocol Smoke Tests
```bash
# Test SecAgg+ masking, unmasking, 0-2 dropouts, and below-threshold abort
python tools/fcs_fl.py test-secagg

# Test Opacus DP-SGD gradient clipping, noise addition, and RDP accountant
python tools/fcs_fl.py test-dp
```

### 2.3 Running Federated Training
```bash
# Run baseline research training (FedAvg, 3 rounds, IID partitions)
python tools/fcs_fl.py run --profile research --rounds 3 --partition iid

# Run protected training (SecAgg+ and Opacus DP-SGD, 3 rounds, moderate non-IID)
python tools/fcs_fl.py run --profile protected --rounds 3 --partition moderate-non-iid
```

### 2.4 Candidate Models & Reports
```bash
# List all registered federated candidate models
python tools/fcs_fl.py candidates list

# Generate machine-readable JSON status report
python tools/fcs_fl.py report
```

---

## 3. Running Automated Test Suites

The test suite contains 36 comprehensive tests covering unit, security, recovery, performance, and integration layers:

```bash
# Run all Phase 6 federation tests
python -m pytest tests/federation-unit tests/federation-security tests/federation-recovery tests/federation-performance tests/federation-integration -v

# Run Phase 1-5 regression tests to ensure no breaking changes
python -m pytest tests/unit/test_phase4_regressions.py tests/unit/test_phase5_integration.py -v
```

---

## 4. Full Experimental Matrix & End-to-End Demo

### 4.1 Execute 16-Experiment Matrix (E6-01 to E6-16)
```bash
python scripts/run_phase6_experiments.py
```
Output results will be written to `artifacts/federation/reports/phase6_experiments_results.json`.

### 4.2 Execute 12-Step Autonomous End-to-End Demonstration
```bash
python scripts/run_phase6_demo.py
```

### 4.3 Run Release Gate G04/G05 Verification Audit
```bash
python scripts/verify_phase6.py
```
This updates `phase6_status.json` with current verification checks and timestamps.

---

## 5. Web UI & API Verification

### 5.1 Backend FastAPI
```bash
uvicorn services.api.src.fcs_api.app:app --port 8000
```
Key Endpoints:
- `GET /v1/federation/status`
- `GET /v1/federation/participants`
- `GET /v1/federation/rounds`
- `GET /v1/federation/models`
- `GET /v1/federation/privacy-status`
- `GET /v1/federation/health`

### 5.2 React Security Dashboard
```bash
cd apps/security-dashboard
npm run dev
```
Navigate to `http://localhost:5173/` and click the **Federated Learning** tab in the sidebar to view:
- Live round status and participant health cards.
- Cumulative differential privacy consumption gauges.
- Interactive SecAgg+ dropout simulation tool.
- Benchmark comparisons and candidate model governance.
