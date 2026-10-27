# Phase 8 Service Degradation & Subsystem Isolation

## 1. Principles of Graceful Degradation
Federated Cyber Shield (FCS v1.2) is designed with decoupled availability planes. The per-event intrusion detection plane must never experience availability loss due to outages in the training plane, the governance blockchain, or post-quantum cryptographic services.

## 2. Subsystem Failure & Safe Degradation Map

| Subsystem Experiencing Failure | Upstream / Downstream Impact | Safe Degraded Behavior | Operator / System Recovery |
|---|---|---|---|
| **Flower Federation Coordinator** | Scheduled federated training round cannot complete | **Detection continues 100% unaffected.** Inactive candidates remain unpromoted. Client privacy budgets preserved. | Coordinator restarts; clients wait for next scheduled round window. |
| **Fabric Consortium Ledger** | Model release manifests and audit batches cannot commit | **Detection continues 100% unaffected.** Outbox relay queues audit events locally in SQLite outbox table. | Upon ledger recovery, outbox automatically flushes batches to SmartBFT ordering service. |
| **DDoS / Scanning Specialist Model**| Specialist inference times out (>50ms deadline) | **Router bypasses timed out specialist.** Evidence fusion marks `UNCERTAIN` flag and uses Level-1 General Detector + Anomaly scores. | Specialist pool auto-scales or restarts; fusion resumes multi-model weighting. |
| **General Intrusion Detector (ML)** | LightGBM inference crashes or encounters corrupted tensor | **FCS-HMD falls back to Anomaly Detector + Rules-Only engine.** Telemetry continues being evaluated without drops. | Alert raised on dashboard; administrator can trigger model bundle rollback. |
| **Tenant Anomaly Detector** | IsolationForest model fails or tenant profile missing | **General Detector operates standalone.** Threat severity flags indicate anomaly context is missing. | Baseline profile regenerated via scheduled tenant background job. |
| **Notification Service / SSE** | WebSocket / SSE client disconnects | **Incident creation and action journaling proceed normally.** Frontend dashboard falls back to REST periodic polling. | Client UI transparently reconnects and refreshes from `/v1/incidents`. |
| **Telemetry Exporter (Silence)** | Border router stops sending flow records | **Observability tracker flags exporter DEGRADED / UNKNOWN.** System raises security alert; never reports 0 threats when blind. | Operator alerted to check exporter routing and UDP collector status. |
| **Firewall Simulator** | Rule application fails or device unreachable | **Action status updated to FAILED.** Incident remains in `ACTION_PENDING`. Alarms generated on SOC dashboard. | Responder alerted to re-attempt or switch to alternative gateway target. |

## 3. Strict Safety Guarantees
1. **Never Report Zero Threats for Zero Telemetry:** An absence of exporter packets is treated as an operational anomaly, not as evidence of network safety.
2. **Never Downgrade to Plaintext:** Federated learning dropouts never trigger an insecure plaintext model update fallback.
3. **Never Fall Back to AUTO:** Response policy errors or outages never cause the system to automatically execute firewall actions.
