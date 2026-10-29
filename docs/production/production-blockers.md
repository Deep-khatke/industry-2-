# Federated Cyber Shield (FCS) v1.2 — Production Blockers & Hardware Qualification Prerequisites

## 1. Zero-Cost Policy Boundary

Federated Cyber Shield has been developed, tested, and verified under a mandatory **₹0 / $0 budget policy**. To maintain absolute zero-cost compliance, no commercial cloud infrastructure (AWS/GCP/Azure), billable managed services, or proprietary hardware appliances have been provisioned.

The following items are recognized as **Production Blockers** preventing unattended live deployment to production telecommunications carrier infrastructure.

---

## 2. Inventory of Production Blockers

### Blocker 1: Gate G13 — Physical Router Hardware Qualification (`AUTO_LIVE`)
- **Status:** **BLOCKED / NOT_ENABLED**
- **Description:** Gate G13 authorizes autonomous edge mitigation rules on physical core routers (e.g., Cisco IOS-XR, Juniper Junos, Arista EOS via BGP Flowspec or Netconf/YANG).
- **Prerequisites for Unblocking:**
  1. Provisioning of physical or high-fidelity simulated hardware testbeds under an isolated network grant.
  2. Completion of Phase 10 qualification protocol (`docs/phase-reports/PHASE10_HANDOFF.md`).
  3. BGP Flowspec rate-limiting stability tests under line-rate 100Gbps telemetry.
  4. Multi-party ISP consortium governance approval for automated route withdrawal.

### Blocker 2: Hardware Security Modules (HSM) for Post-Quantum Root Keys
- **Status:** **BLOCKED FOR SOVEREIGN HOSTING**
- **Description:** In local development and integration testing, dual ECDSA P-256 and ML-DSA-65 keys are generated using cryptographically sound software entropy (`os.urandom`) and persisted in memory/protected local storage.
- **Prerequisites for Unblocking:**
  1. Integration with FIPS 140-3 Level 3 compliant Hardware Security Modules (e.g. YubiHSM2, Thales Luna, or Nitrokey HSM).
  2. Formal post-quantum certificate authority hierarchy and mTLS key distribution.

### Blocker 3: Live ISP Carrier Peering & AS-Level Data Sharing
- **Status:** **BLOCKED**
- **Description:** Real-world federated learning across independent commercial Tier-1/Tier-2 ISPs requires legal inter-carrier data processing agreements (DPA) and BGP peering cross-connects.
- **Prerequisites for Unblocking:**
  1. Multi-carrier legal frameworks establishing liability bounds under automated threat intelligence sharing.
  2. Dedicated low-latency MPLS/VPN inter-ISP federation tunnels.

---

## 3. Safe Operating Mode in Interim

Until all blockers are resolved under funded sovereign programs:
1. FCS **MUST** operate with `AUTO_RESPONSE_ENABLED=False`.
2. All defensive actions must execute exclusively through the **Firewall Simulator**.
3. All telemetry replay must operate against isolated, synthetic, or anonymized datasets.
