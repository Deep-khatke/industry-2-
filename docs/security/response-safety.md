# Federated Cyber Shield (FCS) v1.2 — Defensive Response Safety & Firewall Simulator

## 1. Safety Architecture & Human Approval Gate

Defensive network actions (e.g., blackholing IPs, rate-limiting subnets) have catastrophic failure modes if executed incorrectly on carrier-grade routers. FCS Architecture v1.2 enforces fail-safe controls to ensure no unauthorized or destructive actions occur.

```mermaid
flowchart TD
    Incident[Detected Incident (DDoS / PortScan)] --> ActionCandidate[Generate Recommended Action]
    ActionCandidate --> HumanGate{Human Operator Approval (RBAC: SECURITY_ADMIN)}
    
    HumanGate -- Rejected --> Cancelled[Action Cancelled & Logged]
    HumanGate -- Approved --> PolicyEngine[Tenant Policy Guard]
    
    subgraph PolicyChecks["Automated Policy Invariants"]
        PolicyEngine --> AllowlistCheck{Target in Protected Allowlist?}
        AllowlistCheck -- Yes --> PolicyViolation[ABORT: Protected Target Violation]
        AllowlistCheck -- No --> DurationCheck{TTL within [60s, 86400s]?}
        DurationCheck -- No --> BoundsViolation[ABORT: TTL Out of Bounds]
        DurationCheck -- Yes --> Simulator[Execute in Firewall Simulator]
    end

    Simulator --> StateJournal[Append to Immutable Action Journal]
    StateJournal --> AutoLiveGate{"Gate G13: AUTO_LIVE Enabled?"}
    AutoLiveGate -- "Strictly Blocked" --> Halt[Action Contained in Simulator]
    AutoLiveGate -.->|Future Physical Grant| PhysicalRouter[Physical Core Router]
```

---

## 2. Mandatory Response Invariants

1. **Human-in-the-Loop Approval**:
   - `TIER_1_ANALYST` can review incidents and prepare draft actions, but CANNOT approve them.
   - Only `SECURITY_ADMIN` can issue action approval.
2. **Protected Infrastructure Allowlists**:
   - Critical network infrastructure targets (e.g., DNS root/recursive resolvers, upstream default gateways, internal telemetry collectors) are permanently hardcoded in the protected allowlist.
   - Any action targeting a protected IP is rejected with an HTTP `422 Unprocessable Entity` or `400 Bad Request`.
3. **Bounded Action Lifetimes (TTL)**:
   - Mitigation rules must define an explicit Time-To-Live between 60 seconds and 86,400 seconds (24 hours).
   - Indefinite blackholing is strictly prohibited.
4. **Simulator Containment**:
   - All defensive operations execute within `FirewallSimulator`.
   - Gate G13 (`AUTO_LIVE`) is strictly disabled in code and runtime configuration.
