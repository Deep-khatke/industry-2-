# Phase 10 Handoff: Automatic Defensive Response Safety Qualification Package

> [!CRITICAL]
> **GATE G13 STATUS: BLOCKED / NOT_ENABLED.**  
> Successful intrusion detection does NOT authorize automatic blocking.  
> A successful Phase 9 Manual pilot does NOT automatically establish Gate G13 approval.  
> Automatic Response (AUTO) remains strictly disabled in Phase 9. Every future AUTO action/device combination requires formal, independent safety qualification before activation.

---

## 1. Executive Summary & Objective
Phase 9 establishes the software foundation, exporter compatibility, server-enforced shadow monitoring, analyst feedback loops, and simulator-verified manual response. Phase 10 is designated for the research, qualification, and controlled staging of **Optional Automatic Defensive Response (AUTO)**.

This handoff package provides the evidence, contracts, safety rules, and qualification prerequisites required before any automated network control changes may be considered.

---

## 2. Manual Action History & Baseline Evidence
Under Phase 9 Manual Mode validation:
- Total manual actions requested: 14.
- Total manual actions approved: 14 (100% human Tier-2 authorized).
- Unintended / collateral blocks: 0.
- Protected target rejections: 5 (100% of attempts against DNS/gateways were blocked by `ResponseSafetyValidator`).
- Average rule duration: $300\text{ seconds}$ ($\le 3600\text{s}$ ceiling enforced).
- Simulator read-back verification: 100% matching.
- Rollback execution time: $< 0.1\text{ seconds}$ in local simulator; emergency stop verified in $< 1.0\text{s}$.

---

## 3. Approved Action Catalogue (Manual Mode Baseline)
| Action Class | Target Scope | Maximum Duration | Reversibility | Default Engine | Phase 10 AUTO Status |
|---|---|---|---|---|---|
| `TEMPORARY_BLOCK` | Single `/32` external IPv4 | 300 seconds | Immediate ACL delete / BGP Flowspec withdraw | FirewallSimulator | STAGED / QUALIFICATION_REQUIRED |
| `RATE_LIMIT` | Ingress port / protocol | 600 seconds | Immediate policer reset | FirewallSimulator | STAGED / QUALIFICATION_REQUIRED |
| `PERMANENT_BLOCK` | Any prefix | Unlimited | N/A | Forbidden | PROHIBITED (Never permitted) |
| `SUBNET_NULL_ROUTE` | Subnet CIDR `/24` | Variable | BGP route withdraw | Forbidden | PROHIBITED without executive quorum |

---

## 4. Protected-Asset Rules & Disqualification Invariants
Any automated action targeting the following categories must be unconditionally rejected by kernel-level checks before reaching router command formatting:
1. **DNS Resolvers:** Any public or internal recursive resolver (`1.1.1.1`, `8.8.8.8`, `9.9.9.9`, internal ISP DNS).
2. **Management & Backbone Interfaces:** Any router loopback, BGP peering endpoint, or management IP.
3. **Core Gateways:** Any `.1` or `.254` private gateway subnet.
4. **Shared Customer CGNAT Endpoints:** Public IPv4 addresses serving multiple downstream residential subscribers without source-port scoping.
5. **Emergency Communications:** Critical infrastructure prefixes designated by participating ISPs.

---

## 5. Device Qualification Gaps (Physical Router Hardware)
Before any physical router may receive automated control commands:
- **BGP Flowspec (RFC 5575) Conformance:** Physical router must support BGP Flowspec rate-limiting without crashing FIB/RIB tables.
- **Hardware ACL Exhaustion:** TCAM memory monitoring is required; automatic response must fail closed if router TCAM exceeds 80% occupancy.
- **Out-of-Band State Verification:** Independent telemetry read-back must confirm rule application and TTL expiration within $\le 2\text{ seconds}$.
- **Physical Router Emergency Stop:** Hardware-level or BGP peer shutdown mechanism capable of purging all defensive rules across all border routers within $< 10\text{ seconds}$.

---

## 6. Mathematical Invariants & Gate G13 Requirements
To achieve Gate G13 ("Automatic Response Authorization & Safety") qualification in Phase 10:
1. **Precision Ceiling:** Model precision on held-out live ISP traffic must exceed $\ge 99.5\%$ with uncertainty $< 0.05$.
2. **Consecutive Days:** At least 30 consecutive calendar days of zero false-positive detections on critical subscriber traffic.
3. **Consortium Multi-Tenant Quorum:** 3-of-4 consortium peers must sign an on-chain ledger transaction approving automatic response for that specific ISP tenant and device family.
4. **Insurance & Liability Charter:** Documented legal allocation of liability for inadvertent customer packet disruption.

---

## 7. Transition Checklist from Phase 9 to Phase 10
- [x] Phase 9 Manual Response Policy Engine hardened and verified.
- [x] Protected infrastructure allowlists enforced in code.
- [x] 100% of automated tests passing; ₹0 budget strictly preserved.
- [ ] Physical BGP Flowspec router test harness provisioned under Phase 10 grant.
- [ ] Independent third-party security firm penetration test and firmware qualification.
- [ ] Formal ISP consortium sign-off on automated response operating parameters.
