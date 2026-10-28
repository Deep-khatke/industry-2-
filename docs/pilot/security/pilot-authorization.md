# Real ISP Pilot Authorization & Legal Policy

## 1. Non-Negotiable Authorization Policy
A production rural Internet Service Provider (ISP) network carries real subscriber traffic, enterprise workloads, and critical infrastructure. Under no circumstances may FCS software interact with live customer network equipment without explicit, multi-party written authorization.

## 2. Mandatory Pre-Authorization Requirements
Before any physical connection, export redirect, or shadow telemetry ingestion occurs:
1. **Identified Participating Entity:** Legally registered corporate entity name, operating ASN, and country of registration.
2. **Written Authorization:** Signed Consortium Participation Agreement and Subscriber Data Governance Charter.
3. **Approved Technical Contact:** Dedicated primary and secondary NOC contacts with escalation authority.
4. **Defined Network Scope:** Explicit CIDR prefixes, observation domain IDs, and monitored interfaces.
5. **Approved Telemetry Sources:** IP addresses and export protocols of designated border routers.
6. **Data Minimization Approval:** Agreement that only Layer 3/4 flow metadata is collected (payload captures strictly prohibited).
7. **Documented Cost Ownership:** Absolute verification that no billable infrastructure will generate charges to the user.
8. **Emergency Stop (Kill-Switch):** Approved procedure and authorization to instantaneously halt collection and rollback rules.

## 3. Strict Prohibitions
- **NO Port Scanning:** Never scan external subnets or public IP ranges looking for open NetFlow ports.
- **NO Autonomous Router Modifications:** Never dispatch configuration changes, SSH commands, or NETCONF calls without Tier-2 human responder approval.
- **NO Real Telemetry Leakage:** Real ISP telemetry must never be committed to GitHub or public repositories.
- **NO Billing Surprises:** Do not activate promotional-credit or pay-as-you-go cloud services.

## 4. Operational Invariant
If written authorization or zero-cost cloud resources are unavailable, the system remains in **MODE A (ZERO-COST SYNTHETIC PILOT)**. Mode B is kept deployable but marked `LIVE_PILOT_BLOCKED`.
