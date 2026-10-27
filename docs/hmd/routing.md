# FCS-HMD Conditional Specialist Model Routing
## Dynamic Dispatch, Triggers, and Short-Circuit Optimization

**Subsystem:** FCS-HMD  
**Architecture:** Version 1.2  
**Implementation:** `services/ml_training/src/fcs_ml/hmd/router.py`  

---

## 1. Routing Rationale & Architecture

Executing every specialist for every 30-second feature window is computationally wasteful on resource-constrained rural ISP edge hardware. `ConditionalModelRouter` introduces low-overhead ($24.9\,\mu\text{s}$ p95) conditional routing:

```text
               +---------------------------+
               | Level 1 General & Anomaly |
               +-------------+-------------+
                             |
                             v
               +---------------------------+
               | Conditional Model Router  |
               +-------------+-------------+
              /              |              \
             /               |               \
    Normal Baseline    Volumetric Burst    SYN Scan Probe
           |                 |                   |
           v                 v                   v
     [SHORT-CIRCUIT]    [ROUTE DDoS]     [ROUTE SCANNING]
   Bypass Specialists   Specialist Runs   Specialist Runs
```

---

## 2. Routing Decision Policy

### A. Short-Circuit Benign Baseline
If all of the following conditions hold:
- Level 1 General Threat Score $< 0.35$
- Level 1 Anomaly Probability $< 0.40$
- No volumetric burst triggers
- No port scan probe triggers

The router **short-circuits** execution: all specialists are marked `BYPASSED`, saving CPU compute.

### B. Volumetric DDoS Triggers
The DDoS specialist is routed if:
- Level 1 General Threat Score $\ge 0.35$, OR
- Byte sum $> 200,000$ bytes, OR
- Packet sum $> 1,000$ packets, OR
- Flow rate $> 2.0\,\text{MB/s}$

### C. Port Scan & Reconnaissance Triggers
The Scanning specialist is routed if:
- Level 1 General Threat Score $\ge 0.35$, OR
- Flow has TCP SYN flag set (`TCP_FLAGS == 2` or `0x02` without ACK `0x10`) with low packet count ($< 10$), OR
- Destination port matches sensitive probe list (21, 22, 23, 25, 110, 143, 445, 1433, 3306, 3389, 5432).

### D. Botnet Specialist Eligibility Check
Before routing, `ConditionalModelRouter` checks if required features (`DNS_QUERY_ID`, `DNS_QUERY_TYPE`, `DNS_TTL_ANSWER`, `SRC_TO_DST_AVG_THROUGHPUT`) exist. In FlowEvent v1, these features are missing, so the botnet specialist is logged as `BOTNET_SPECIALIST_BYPASSED: Ineligible` without failing the pipeline.
