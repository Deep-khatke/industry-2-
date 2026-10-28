# ISP Pilot Onboarding Guide

## 1. Overview
The Federated Cyber Shield (FCS) v1.2 Phase 9 ISP Onboarding System manages the end-to-end lifecycle of prospective and participating rural Internet Service Providers. In strict adherence to the ₹0 budget and ISP authorization policies, onboarding proceeds through auditable gates without authorizing live customer packet inspection or network control modification until all prerequisite criteria are satisfied.

## 2. Onboarding Lifecycle States
```
       +-------+
       | DRAFT |
       +---+---+
           | (Profile completeness, contact verification)
           v
+-----------------------+
| AUTHORIZATION_PENDING |
+----------+------------+
           | (Signed written participation agreement, zero-cost confirmation)
           v
   +------------------+
   | TECHNICAL_REVIEW |
   +-------+----------+
           | (Exporter capability registration, FeatureSpec parity >= 85%)
           v
   +-----------------+
   | SECURITY_REVIEW |
   +-------+---------+
           | (Tenant isolation, DP accounting, protected targets locked)
           v
  +------------------+
  | READY_FOR_SHADOW |
  +--------+---------+
           | (Dual human authorization, emergency kill-switch verified)
           v
   +---------------+       (7 calendar days)       +------------------+
   | SHADOW_ACTIVE +------------------------------>+ SHADOW_COMPLETED +--> PILOT_CLOSED
   +-------+-------+                               +------------------+
           |
           +---------------------> PILOT_PAUSED / PILOT_BLOCKED
```

## 3. Required Onboarding Fields
- **Pilot Identifier:** Unique string (e.g. `pilot-sim-001`, `pilot-real-001`).
- **Tenant Identifier:** Immutable tenant binding (e.g. `rural-isp-alpha`).
- **ISP Display Name:** Registered business entity name and ASN.
- **Environment Mode:** `MODE_A_SYNTHETIC`, `MODE_B_REAL_SHADOW`, or `MODE_C_MANUAL_VALIDATION`.
- **Authorized Network Scope:** Bounded CIDR prefixes and IPFIX observation domain IDs.
- **Technical Contact:** Operational email and 24/7 NOC emergency contact.
- **Exporter Inventory:** Router vendor, model, protocol (IPFIX/NetFlow v9), source IP, export frequency, and sampling rate.
- **Data Retention Limits:** Raw telemetry (max 7 days), incident records (90 days).

## 4. State Transition Prerequisites
| Transition | Required Role | Mandatory Prerequisites |
|---|---|---|
| DRAFT &rarr; AUTHORIZATION_PENDING | TENANT_ADMIN | All profile fields populated; network scope bounded. |
| AUTHORIZATION_PENDING &rarr; TECHNICAL_REVIEW | PLATFORM_ADMIN | Written consortium participation charter; ₹0 spend verification. |
| TECHNICAL_REVIEW &rarr; SECURITY_REVIEW | PLATFORM_ADMIN | Exporter parser template verified; FeatureSpec parity verified. |
| SECURITY_REVIEW &rarr; READY_FOR_SHADOW | PLATFORM_ADMIN | Tenant isolation verified; protected assets allowlist locked. |
| READY_FOR_SHADOW &rarr; SHADOW_ACTIVE | TENANT_ADMIN / PLATFORM_ADMIN | Server-enforced Shadow Mode enabled; AUTO response disabled. |

## 5. Live Pilot Blockers
If written legal authorization or dedicated zero-cost cloud tenant infrastructure is pending, the onboarding profile must remain in state `PILOT_BLOCKED` with reason code `LIVE_PILOT_BLOCKED`.
