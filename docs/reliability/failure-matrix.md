# Phase 8 Resilience & Fault Injection Matrix (F01–F30)

## Overview
All 30 bounded failure injection scenarios were executed using the deterministic Fault Injection Engine (`tools/phase8/fault_injector/engine.py`).  
Summary: **30 of 30 Faults Tested — 30 PASSED (100% Graceful Recovery Rate)**

| Fault ID | Target Component | Injected Fault | Expected Safe Behavior | Observed Recovery Behavior | Residual Risk | Status |
|---|---|---|---|---|---|---|
| **F01** | IPFIX Collector | Process crash during header parse | Stream sinks retain buffered flows; collector reboots | Buffer preserved; parser re-reads stream | Transient flow lag | **PASS** |
| **F02** | Stream Adapter | Ingestion buffer capacity overflow | Drop/quarantine with `SinkCapacityExceeded` metric | Dropped records recorded in metrics; no crash | Unbuffered telemetry loss | **PASS** |
| **F03** | Telemetry Ingestion | Duplicate event replay | Ingestion deduplicates by sequence; metrics logged | Duplicate count incremented; single downstream record | Minor queue lag | **PASS** |
| **F04** | Feature Engine | Corrupted/missing locked feature | Validation fails; fallback to `RULES_ONLY` mode | FeatureSpec error caught; rules fallback activated | Coarser detection | **PASS** |
| **F05** | Model Registry | Corrupted model pickle / artifact | Admission rejects file; previous model kept | SHA-384 mismatch detected; model unchanged | Stale model version | **PASS** |
| **F06** | General Detector | Inference execution timeout (>50ms) | Route directly to Anomaly + Rules-Only fallback | Timeout caught; rules-only score returned | Absence of ML score | **PASS** |
| **F07** | Anomaly Detector | Anomaly model service unavailable | General detector operates standalone; log warning | Degraded status logged; incident engine flags score | Missing anomaly context | **PASS** |
| **F08** | Specialist Model | DDoS specialist timeout (>50ms) | Evidence fusion marks UNCERTAIN flag and proceeds | Specialist bypassed; level-1 score fused | Reduced attack context | **PASS** |
| **F09** | Evidence Fusion | High-disagreement conflict between models | Fusion marks UNCERTAIN; escalates to Tier-1 review | Uncertainty flag set; human triage alerted | Analyst review needed | **PASS** |
| **F10** | Incident Database | SQLite operational error / lock | Transaction rolls back; zero partial state written | Rollback verified; table row count unchanged | Transient retry delay | **PASS** |
| **F11** | Outbox Relay | Process restart during pending commit | Outbox re-reads uncommitted entries on reboot | Relay resumes idempotently without double-commit | Minor commit delay | **PASS** |
| **F12** | Notification Svc | Client connection drop during SSE | Worker suppresses broken pipe; closes channel | Channel closed; reconnect polling succeeds | Stale dashboard until poll | **PASS** |
| **F13** | Backend API | Web server restart with active jobs | State restored from persistent SQLite tables | Tenants, incidents, and audit history verified | In-flight HTTP retry | **PASS** |
| **F14** | Frontend Dashboard| Network disconnect during poll | Client caches state; displays degraded banner | Dashboard re-synchronizes upon reconnect | UI alert delay | **PASS** |
| **F15** | FL Coordinator | Server crashes during active round | Round aborted cleanly; zero budget refunded | Round aborted; clients disconnect safely | Abandoned round compute | **PASS** |
| **F16** | Federated Client | 2 client dropouts (5 of 7 remaining)| Quorum maintained (>=5); round completes | SecAgg+ successfully unmasks with 5 peers | Slightly reduced sample | **PASS** |
| **F17** | SecAgg+ Protocol | 3 client dropouts (<5 quorum) | Protocol aborts round; no plaintext weights leaked| Aborted; zero unmasked updates logged | Compute re-run required | **PASS** |
| **F18** | DP Accountant | Corrupted budget database state | Fails closed; halts training until reconciled | Error raised; tenant training barred | Training halted | **PASS** |
| **F19** | Fabric Ledger | Consortium blockchain network outage | Inference plane queues audit events to outbox | Ingestion & detection continue with 0 drops | Outbox buffer growth | **PASS** |
| **F20** | Fabric Chaincode | Invalid transaction submitted | Transaction rejected; outbox marks REJECTED | Rejected; error journaled; no ledger corrupt | Model not activated | **PASS** |
| **F21** | Cryptographic Key | Signing key revoked in trust store | Signature verification fails; reject manifest | Revocation recognized; manifest rejected | Stale release blocked | **PASS** |
| **F22** | Model Promotion | Attempted promotion of revoked model | Rollback engine raises `RollbackSecurityError` | Promotion blocked; previous model active | Stale active model | **PASS** |
| **F23** | Firewall Simulator| Simulator database unreachable | Action journal marks FAILED; alarms raised | Error logged; incident remains ACTION_PENDING | Unmitigated threat | **PASS** |
| **F24** | Firewall Simulator| Rollback failure during revocation | Rule flagged for manual operator remediation | Rule status marked ERROR_REQUIRING_AUDIT | Lingering rule in dev | **PASS** |
| **F25** | Ingestion Engine | Exporter stops sending (stale telemetry)| Observability flags exporter UNKNOWN/DEGRADED | Security warning raised; never reports 0 risk | Threat visibility blind | **PASS** |
| **F26** | Storage Layer | Disk quota near exhaustion in testbed | Collector sheds non-critical metrics; logs alarm | Emergency quota protocol logged; DB clean | Log shedding | **PASS** |
| **F27** | System CPU | Bounded CPU saturation (4 worker threads)| Scheduler sheds background tasks; keeps inference | Core detection p95 latency stays < 5000ms | Background tasks delayed| **PASS** |
| **F28** | System Memory | Bounded memory pressure (50MB buffer) | Buffer capped at max capacity; old data purged | RSS memory stayed within bounds; 0 OOM | Older flows evicted | **PASS** |
| **F29** | Service Life Cycle| Restart while flow processing in-flight | Recovery reconciliation repairs stream pointer | Restart verified; zero duplicate incidents | Brief pause in stream | **PASS** |
| **F30** | Database Recovery | Point-in-time restore from backup | Restore completes in <1s; all records verified | Restored SQLite verified identical to backup | Post-backup event lag | **PASS** |
