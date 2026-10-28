# Incident Escalation Matrix & Emergency Stop Procedures

## 1. Incident Lifecycle State Graph
```
NEW &rarr; ACKNOWLEDGED &rarr; INVESTIGATING &rarr; ACTION_RECOMMENDED &rarr; ACTION_PENDING_APPROVAL &rarr; SIMULATED_ACTION_VERIFIED &rarr; RESOLVED / FALSE_POSITIVE &rarr; CLOSED
```

## 2. Severity Escalation Matrix
| Escalation Tier | Trigger Condition | Assigned Role | Target SLA | Action Authority |
|---|---|---|---|---|
| INFORMATIONAL | Anomaly score 0.70-0.79 | Tier-1 Analyst | 60 min | Observational logging |
| REPEATED_SUSPICIOUS | 3+ scans from same subnet | Tier-1 Analyst | 15 min | Recommend Manual Action |
| HIGH_SEVERITY | DDoS / SYN flood > 50 Mbps | Tier-2 Responder | 5 min | Approve Simulated Action |
| CRITICAL_ATTACK | Core link congestion threat | Lead Network Eng | 2 min | Executive Dual-Approval |
| TELEMETRY_LOSS | Exporter stream lag > 90s | ISP NOC Lead | 10 min | Interface check / reboot |
| MODEL_FAILURE | Inference timeout > 500ms | Applied ML Eng | 5 min | Execute Model Rollback |
| EMERGENCY_STOP | Rogue action / service impact | Platform Admin | < 10 sec | Instant Rule Rollback |

## 3. Emergency Kill-Switch Procedure
In the event of an unintended customer block or false positive impacting legitimate services:
1. Trigger Emergency Stop via API or CLI:
   ```bash
   python -c "from fcs_pilot.operations.escalation import IncidentEscalationManager; IncidentEscalationManager().trigger_emergency_pause('admin', 'Kill-switch invoked')"
   ```
2. The system executes instantaneous rollback of all active simulated firewall rules in $< 10$ seconds.
3. Collection is suspended until NOC verifies root cause.
