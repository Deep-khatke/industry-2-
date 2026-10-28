# Shadow Monitoring Operational Runbook

## 1. Purpose
This runbook guides SOC engineers and network operators on executing server-enforced Shadow Monitoring during Phase 9. Shadow Mode observes and scores real or synthetic traffic while guaranteeing that zero network-control modifications can be made.

## 2. Server-Enforced Configuration
Verify that shadow mode is active via CLI or API:
```bash
python -m fcs_pilot.cli status
```
Output must confirm:
```
Response Mode: MANUAL_ONLY (AUTO DISABLED)
Network Action Executed: False
Execution Default: FIREWALL_SIMULATOR_DEFAULT
Server-Enforced Shadow Mode: True
```

## 3. Daily Operational Verification Steps
1. **Verify Exporter Ingestion:**
   Check `/v1/pilot/coverage` to confirm stream lag is $< 15.0\text{s}$ and exporter status is `ONLINE`.
2. **Review Model Scoring Queue:**
   Verify windows scored matches expected flow volume ($\approx \frac{\text{flows}}{100}$).
3. **Inspect Candidate Incidents:**
   Check `/v1/pilot/incidents` for candidate threats. Ensure all recommendation execution statuses read `ADVISORY_ONLY_NOT_EXECUTED`.
4. **Monitor Sequence Numbers:**
   Alert NOC if sequence gaps $> 5$ are detected on any exporter interface.
