# FCS-HMD Operational Runbook
## Operator & SOC Administrator Guide for Hierarchical Threat Detection

**Subsystem:** FCS-HMD  
**Architecture:** Version 1.2  
**Target Audience:** SOC Analysts, Security Engineers, and Rural ISP Administrators  

---

## 1. Quick Verification & Health Inspection

To verify the operational status of the FCS-HMD detection engine from the command line:

```bash
# Inspect active engine, bundle digest, and loaded models
python tools/fcs_hmd.py inspect

# Test conditional router branch logic
python tools/fcs_hmd.py route-test

# Test evidence fusion synthesis
python tools/fcs_hmd.py fusion-test

# Score an ad-hoc test flow vector
python tools/fcs_hmd.py predict --tenant rural-isp-alpha
```

---

## 2. Managing Detection Bundles

### List Registered Bundles
```bash
python tools/fcs_hmd.py bundles list
```

### Verify Bundle Integrity Hashes
```bash
python tools/fcs_hmd.py bundles verify --bundle-id fcs-hmd-bundle-v1
```

### Activate a Verified Bundle
```bash
python tools/fcs_hmd.py bundles activate --bundle-id fcs-hmd-bundle-v1 --role PLATFORM_ADMIN
```

### Emergency Bundle Rollback
If a newly activated bundle causes anomalous false alarms or latency spikes:
```bash
python tools/fcs_hmd.py bundles rollback --role PLATFORM_ADMIN
```

---

## 3. Investigating Incidents in SOC Dashboard

1. **Navigate to Incident Forensics:**
   Open the **Incidents Page** in the React SOC Dashboard.
2. **Review Multi-Model Evidence Card:**
   Each incident displays:
   - Level 1 General Detector calibrated threat probability
   - Level 1 Tenant Anomaly model score
   - Specialist outputs (DDoS volumetric probability or Scanning probe probability)
   - Matched behavioral rules (e.g. `FCS-R101` SYN Flood Rate Alert)
   - Composite risk tier and primary attack category
3. **Review Recommended Manual Mitigation:**
   - Review proposed action type (e.g. `TEMPORARY_BLOCK`) and target IP.
   - Click **Approve Mitigation** to simulate execution.
   - Note: Automated mitigation is permanently disabled.

---

## 4. Replaying Threat Scenarios

To test detection behavior against reproducible traffic profiles:

```bash
# Replay normal traffic (verifies short-circuiting)
python tools/fcs_hmd.py replay --scenario normal --tenant rural-isp-alpha

# Replay volumetric DDoS flood
python tools/fcs_hmd.py replay --scenario ddos --tenant rural-isp-alpha

# Replay stealthy port scan
python tools/fcs_hmd.py replay --scenario portscan --tenant rural-isp-alpha
```

---

## 5. Running the Complete Verification Suite

To run all lint checks, frontend builds, unit tests, integration tests, security tests, monorepo regression, and Gate G15 verification:

```bash
python scripts/verify_phase5.py
```
This generates `phase5_status.json` and updates `docs/phase-reports/phase5-verification.md`.
