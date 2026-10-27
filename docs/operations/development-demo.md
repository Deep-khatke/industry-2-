# Federated Cyber Shield (FCS) v1.2 — Development Demonstration Guide
## Step-by-Step Instructions for Executing the Phase 4 Zero-Cost Cybersecurity MVP

**Budget:** Strictly ₹0 / $0  
**Stack:** Python FastAPI + React/TypeScript Vite SOC Dashboard + SQLite WAL  

---

## 1. Quickstart Commands

Federated Cyber Shield includes a unified CLI tool:

```bash
# 1. Seed development database with 7 ISP tenants and demo accounts
fcs demo seed

# 2. Launch FastAPI backend (serves both REST API and compiled React SOC Dashboard)
fcs api start --port 8000
```

Open your browser and navigate to:
**`http://127.0.0.1:8000/`**

---

## 2. Demonstration Scenarios

### Scenario A — Normal Traffic (Zero False Alarms)
Simulates benign web browsing and internal DNS queries across `rural-isp-alpha`.

```bash
fcs demo replay --scenario normal --tenant rural-isp-alpha
```
- **Expected Outcome:** Monitored flow counter increases; exporter health indicates `HEALTHY`; zero malicious alerts or false positive incidents are generated.

---

### Scenario B — Volumetric Flood / DDoS Burst
Simulates a high-rate UDP/ICMP amplification flood exceeding 100,000 packets and 500 MB.

```bash
fcs demo replay --scenario suspicious --tenant rural-isp-alpha
```
- **Expected Outcome:**
  - Rule `FCS-R101` triggers.
  - ML model evaluates high risk ($P_{\text{threat}} > 0.85$).
  - An incident is created: `"Volumetric Traffic Flood / Potential DDoS Burst"`.
  - Severity: `CRITICAL`.
  - Notification written to transactional outbox.
  - Recommended Action: `TEMPORARY_BLOCK` against attacking IP `198.51.100.42` for 300 seconds.

---

### Scenario C — SYN Port Scanning / Reconnaissance
Simulates a horizontal SYN sweep across critical infrastructure ports (23, 2323, 445, 3389).

```bash
fcs demo replay --scenario scanning --tenant rural-isp-alpha
```
- **Expected Outcome:**
  - Rule `FCS-R102` (SYN Scan) and `FCS-R104` (Critical Port Probe) trigger.
  - Severity: `MEDIUM`.
  - Incident created: `"High-Frequency SYN Port Scan / Network Reconnaissance"`.
  - Recommended Action: `RATE_LIMIT` or `TEMPORARY_BLOCK`.

---

## 3. Human-in-the-Loop Mitigation & Audit Workflow

1. **Log in to SOC Dashboard:**
   - URL: `http://127.0.0.1:8000/`
   - Username: `responder_alpha`
   - Password: `FcsDemo2026!`
2. **Navigate to Incidents:**
   - Click **Incidents** in the sidebar.
   - Inspect the newly created `CRITICAL` DDoS incident.
   - Click on the incident to open the forensic details drawer.
3. **Review Recommended Defensive Action:**
   - Navigate to **Manual Response Center**.
   - Inspect the pending recommendation: `TEMPORARY_BLOCK` for `198.51.100.42`.
4. **Authorize Simulated Mitigation:**
   - Click **Authorize Mitigation**.
   - Review target IP and duration in the confirmation modal.
   - Click **Confirm Mitigation**.
   - The simulator inserts `RULE-<hash>` into the software firewall table.
   - The action status updates to `VERIFIED`.
   - The incident status transitions to `MITIGATED`.
   - Notice the persistent disclaimer: *"Simulated defensive action — no real network device modified."*
5. **Verify Audit Journal & Rollback:**
   - Under **Action Audit Journal**, inspect the immutable record.
   - Click **Rollback** to revoke the simulated firewall rule.
   - The simulator sets status to `REVOKED`, and the journal updates to `ROLLED_BACK`.

---

## 4. Multi-Tenant Isolation Verification

1. Log out or switch to `responder_bravo` (Password: `FcsDemo2026!`).
2. Notice that the incidents, firewall rules, and telemetry records for `rural-isp-alpha` are completely invisible.
3. Attempting to directly request `rural-isp-alpha` incident IDs via the API produces `403 Forbidden`.

---

## 5. Safe Reset Command

To restore the development database to a pristine initial state:

```bash
fcs demo reset
```
*(Restricted strictly to local development SQLite databases).*
