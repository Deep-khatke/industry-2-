# Federated Cyber Shield (FCS) v1.2 — Incident Escalation & Response Protocol

## 1. Role-Based Escalation Matrix

FCS defines strict separation of duties for security analysts and engineers:

| Role Identifier | Assigned Personnel | Permissions & Capabilities | Defensive Mitigation Authority |
|---|---|---|---|
| **TIER_1_ANALYST** | SOC Analyst / Watch Officer | Read alerts, review flow traces, query history, draft mitigation notes | **CANNOT APPROVE** actions |
| **SECURITY_ADMIN** | Lead SOC Engineer / Incident Commander | Full administrative access, modify tenant policy, trigger backups | **AUTHORIZED** to approve actions |
| **SYSTEM_OPERATOR** | Platform / Infrastructure SRE | Service restarts, database backups, log maintenance | **READ-ONLY** on tenant telemetry |

---

## 2. Escalation Workflow Diagram

```mermaid
sequenceDiagram
    autonumber
    participant Sensor as Ingestion & HMD Engine
    participant Tier1 as Tier-1 Analyst (SOC)
    participant Admin as Security Admin (Lead)
    participant Simulator as Firewall Simulator

    Sensor->>Tier1: Raise Severity HIGH Incident (e.g. Volumetric DDoS)
    Tier1->>Tier1: Inspect Flow Headers & Traffic Distribution
    alt False Positive / Benign Traffic
        Tier1->>Sensor: Mark Incident as RESOLVED (Annotated False Positive)
    else True Positive Cyber Attack
        Tier1->>Admin: Escalate Incident with Recommended Mitigation
        Admin->>Admin: Verify Target CIDR & TTL Duration
        Admin->>Simulator: Submit Action Approval
        Simulator-->>Admin: Action Activated in Simulator (Log appended)
    end
```

---

## 3. High-Priority Threat Scenarios

- **DDoS Volumetric Floods**: Automatically prioritized as `CRITICAL`. Immediate recommendation: Rate-limit or blackhole attacking source prefix.
- **Port Scan / Reconnaissance**: Prioritized as `MEDIUM`. Recommendation: Drop scan packets for 1800s.
- **Cross-Tenant Breach Attempt**: System-level `SECURITY_AUDIT` alert dispatched immediately to all tenant administrators.
