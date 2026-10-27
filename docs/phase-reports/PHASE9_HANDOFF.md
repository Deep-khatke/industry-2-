# Phase 9 Handoff: Real ISP Manual Mode Pilot Readiness Package

> [!IMPORTANT]
> **Pilot Status: PREPARATION ONLY — NOT YET COMMENCED.**  
> Phase 8 provides verified software engineering evidence and deterministic simulation benchmarks. In compliance with the strict ₹0 budget and authorization policies, no real ISP contracts were executed, no paid cloud infrastructure was provisioned, and no real router equipment was contacted or modified. Operational validation requires completing the requirements below.

---

## 1. Governance & Consortium Agreements
1. **Consortium Multi-Party Agreement:** Formal legal agreement governing data ownership, model intellectual property, liability allocation, and consortium voting weights among the initial participating ISPs.
2. **Data Ownership & Subscriber Privacy Policy:** Legal warranty that raw subscriber IP addresses and unmasked payload records remain strictly within each ISP's local perimeter. Only differentially private gradient vectors (Opacus DP-SGD, $\epsilon \le 10.0, \delta \le 10^{-5}$) and masked aggregation shares (SecAgg+) leave the ISP boundary.
3. **SmartBFT Ledger Custody:** Establishment of four independent consortium peer nodes hosted on physically separate cloud providers with Hardware Security Module (HSM) key custody.

## 2. Infrastructure & Tenant Account Architecture
1. **Dedicated Tenant Cloud Accounts:** Each ISP must deploy its FCS ingestion stack into an ISP-owned AWS/GCP account. Cross-tenant access must be enforced via independent IAM roles and VPC Peering boundaries rather than software tenant identifiers alone.
2. **Network Connectivity & Exporter Ingress:**
   - Secure IPSec VPN or AWS Direct Connect between ISP border routers and the IPFIX Collector.
   - Verified NetFlow v9 / IPFIX exporter compatibility with template IDs supporting the 14 locked features of FeatureSpec v1.2.
3. **Storage & Retention Budget:**
   - Raw flow retention: Maximum 7 days in encrypted local NVMe/S3.
   - Incident records & action journal: 90 days persistent retention for audit compliance.
   - Privacy accounting ledger: Permanent immutable storage for differential privacy verification.

## 3. Threat Detection & False-Alert Shadow Monitoring
1. **Mandatory 7-Day Shadow Operation:** Before any live response actions are authorized, FCS v1.2 must operate in read-only "Shadow Mode" for a minimum of seven consecutive calendar days on live un-curated ISP traffic.
2. **Operational Alert Rate Target:** Operator target of `<= 5 false grouped incidents per ISP per day`.
3. **Human Analyst Capacity Assumptions:** Assuming an average triage duration of 4 minutes per incident, 5 grouped incidents/day requires <= 20 minutes of Tier-1 SOC analyst review time per ISP shift.
4. **Model Feature Parity Review:** Verification that live router NetFlow templates furnish all 14 live-compatible features without zero-filling or synthetic imputation.

## 4. Manual Response Authority & Router Integration
1. **Manual Mode Exclusivity:** Manual Mode remains the **only** permitted response mode for Phase 9. Automatic Response (AUTO) is strictly disabled and requires a formal multi-tenant safety qualification review before activation.
2. **Dual-Authorization Workflow:** Any temporary rate limit or block action must be reviewed by a certified Tier-1 Analyst and explicitly approved by an authorized Tier-2 Responder (`SECURITY_RESPONDER` or `TENANT_ADMIN`).
3. **Real Device Integration Constraints:**
   - Initial pilot response actions must be applied via BGP Flowspec (RFC 5575) or ephemeral router ACLs with hard-enforced TTLs (`duration_seconds <= 300`).
   - Automated router rollback must be verified out-of-band via scheduled router configuration diff monitoring.
4. **Emergency Stop (Kill-Switch):** A physical or software emergency kill-switch allowing instantaneous rollback of all active defensive rules across all border gateways within `< 10 seconds`.

## 5. Security, Penetration Testing & Cryptographic Audits
1. **Independent Third-Party Penetration Test:** Black-box and white-box security review of the FastAPI REST API, React SOC dashboard, and SQLite/PostgreSQL outbox mechanisms.
2. **Post-Quantum Cryptography Audit:** Review of the ML-DSA-65 (NIST FIPS 204) implementation and RFC 8785 JSON Canonicalization Scheme (JCS) by certified cryptographic security specialists.
3. **HSM Key Custody:** Transition of development ECDSA P-256 and ML-DSA-65 signing keys from software memory stores into FIPS 140-3 Level 3 Hardware Security Modules.

## 6. Target Recovery Objectives (Production SLA)
- **Recovery Point Objective (RPO):** `<= 5 minutes` of telemetry outbox buffer.
- **Recovery Time Objective (RTO):** `<= 15 minutes` for multi-AZ failover of ingestion and detection planes.
- **Inference Availability:** `99.99%` uptime for the per-event detection plane, completely isolated from blockchain or federated training downtime.

## 7. Estimated Production Cost Model (Phase 9 Planning)
While Phase 8 operated with strictly ₹0 spend, a live 3-ISP pilot will incur realistic cloud and network transit costs:
- 3× Dedicated AWS ECS/EKS Ingestion Clusters (m6i.xlarge, Multi-AZ): ~$750 / month
- AWS Managed Streaming for Kafka / Kinesis: ~$320 / month
- Multi-Region PostgreSQL (RDS Aurora Multi-AZ): ~$410 / month
- Fabric Orderer VM Nodes (4 nodes across 3 cloud providers): ~$480 / month
- Estimated Total Monthly Pilot Operational Cost: **~$1,960 / month** (to be funded under Phase 9 consortium grant / budget).
