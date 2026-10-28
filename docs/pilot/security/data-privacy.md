# Subscriber Data Privacy & Tenant Boundary Architecture

## 1. Zero-Egress Invariant
Raw subscriber packet flows, IP addresses, and payload records remain **strictly inside each ISP's local perimeter**. Raw telemetry is never uploaded to GitHub, central servers, or cross-tenant endpoints.

## 2. Privacy Preservation Mechanisms
1. **Differential Privacy (DP-SGD):**
   - Implemented via Opacus with Gaussian noise injection ($\sigma \ge 1.0$).
   - Strict cumulative privacy budget ceiling: $\epsilon \le 10.0, \delta \le 10^{-5}$ per ISP tenant.
   - Exhaustion of privacy budget automatically blocks further training rounds for that tenant.
2. **Secure Aggregation (SecAgg+):**
   - Masked aggregation vectors ensure the central coordinator can only observe the sum of updates, never an individual ISP's gradient vector.
   - Minimum quorum of 5-of-7 ISPs required for unmasking; below quorum, round aborts without plaintext exposure.
3. **Tenant Boundary Isolation:**
   - Multi-tenant token scoping validates caller tenant ID against requested resource.
   - Cross-tenant incident queries return `403 FORBIDDEN` (IDOR defense verified).

## 3. Data Minimization & Retention
- **Raw IPFIX/NetFlow records:** Retained for a maximum of 7 calendar days before rolling deletion.
- **Aggregated feature windows:** Retained for 14 days.
- **Incident evidence:** Retained for 90 days for operational audit compliance.
- **Action journal logs:** Retained for 365 days for immutable defensive auditability.
