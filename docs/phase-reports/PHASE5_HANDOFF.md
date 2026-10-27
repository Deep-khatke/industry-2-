# Federated Cyber Shield (FCS) v1.2 — Phase 5 Handoff Specification
## Hierarchical Multi-Model Engine Integration, Specialist Detection Routing & Evidence Fusion

**From:** Phase 4 Engineering Team  
**To:** Phase 5 Engineering Team  
**Architecture Baseline:** Federated Cyber Shield v1.2  
**Handoff Date:** 2026-10-25  

---

## 1. Phase 4 Deliverables Handoff

Phase 4 delivers an operationally testable, durable cybersecurity MVP:
1. **Durable Telemetry & Feature Windows:** Ingests flow records and partitions into 30s event-time windows with 60s lateness tolerance in [WindowEngine](file:///c:/college/industry%202/services/api/src/fcs_api/telemetry/window_engine.py).
2. **Validated Pre-Deployment Inference:** Loads candidate model `lightgbm_deployable_subset` with verified SHA-256 digest and 14-feature contract parity in [DetectionService](file:///c:/college/industry%202/services/api/src/fcs_api/detection/service.py).
3. **Deterministic Rules & Risk Aggregation:** Evaluates rules FCS-R101 through FCS-R104 and computes explainable 0–100 risk scores.
4. **Persistent Incident Management:** Stores grouped incidents, forensic flow evidence, status history, and transactional notifications.
5. **Security Operations Dashboard:** React 18 / TypeScript interface with 7 operational pages, live polling, and threat feeds.
6. **Manual Response Policy & Firewall Simulator:** Administrator approval workflow with protected IP allowlist, TTL bounds, rollback, and verified simulated execution.

---

## 2. Phase 5 Scope: Hierarchical Multi-Model Routing

Phase 5 introduces a hierarchical ensemble of specialist detection models:

```text
                  Incoming Feature Window (30s)
                               │
                               ▼
               [Level 1: ISP Baseline Anomaly Detector]
                 (Tenant-specific Autoencoder / IForest)
                               │
                ┌──────────────┴──────────────┐
              LOW                           ELEVATED
               │                              │
               ▼                              ▼
      Mark Normal (0.05)            [Conditional Model Router]
                                    │
               ┌────────────────────┼────────────────────┐
               ▼                    ▼                    ▼
       [DDoS Specialist]    [Scan Specialist]    [Botnet Specialist]
         (High volume,        (TCP SYN/RST,        (Periodic beaconing,
          entropy drops)       port fan-out)        flow duration)
               │                    │                    │
               └────────────────────┼────────────────────┘
                                    │
                                    ▼
                         [Evidence Fusion Engine]
                    (Dempster-Shafer / Bayesian Fusion)
                                    │
                                    ▼
                       [Composite Threat Envelope]
```

---

## 3. Extensible Interfaces Prepared for Phase 5

To ensure Phase 5 can add specialist models without modifying Incident Management or Response Policy:

### 3.1 Pluggable Model Evaluator Contract
In `services/api/src/fcs_api/detection/service.py`, Phase 5 can extend `DetectionService.evaluate_window()`:
```python
class SpecialistModelEvaluator(Protocol):
    def evaluate(self, window_features: dict[str, Any]) -> dict[str, Any]:
        """
        Returns:
            {
                "specialist_id": str,
                "score": float, # 0.0 - 1.0
                "confidence": float,
                "attack_category": str,
                "reason_codes": list[str],
            }
        """
        ...
```

### 3.2 Evidence Fusion Engine
Phase 5 should implement evidence fusion that combines:
- Level 1 Anomaly Probability ($P_{\text{anomaly}}$)
- Specialist Model Probabilities ($P_{\text{DDoS}}, P_{\text{Scan}}, P_{\text{Botnet}}$)
- Deterministic Rule Matches ($R_{101} \dots R_{104}$)
into a unified threat evidence object.

### 3.3 Dashboard Model Monitoring Extension
Page 6 (**Model Monitoring**) in `apps/security-dashboard/src/pages/ModelMonitoringPage.tsx` is structured to display multiple specialist cards, latency histograms, and per-specialist score distributions without redesigning the layout.

---

## 4. Invariants to Preserve in Phase 5

> [!CAUTION]
> **Safety Invariant:** Regardless of how many specialist models are added in Phase 5, all model outputs remain purely probabilistic threat evidence. The rule `network_action_executed = False` must be preserved across all inference outputs, and the Manual Response Policy Engine must remain the sole gateway for defensive action execution.
