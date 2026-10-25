# Federated Cyber Shield (FCS) v1.2 — Security Threat Model (Phase 1)

## 1. Threat Assumptions & Attacker Models
The platform assumes the following adversary profiles:
1. **Malicious External Entity**: Seeks to inject forged telemetry, cause denial-of-service via malformed packet floods, or exploit buffer overflows in the parser.
2. **Curious or Hostile Competitor Tenant**: An ISP tenant attempting to observe, exfiltrate, or manipulate telemetry belonging to another rural ISP.
3. **Compromised Exporter Appliance**: An edge router with compromised firmware attempting to spoof another tenant's ID or bypass sampling rates.
4. **Untrusted Platform Operator**: A platform administrator attempting to harvest customer traffic data without authorization.

---

## 2. Threat Analysis & Countermeasures

| Threat ID | Threat Description | Attack Vector | Countermeasure in FCS Phase 1 | Verification Evidence |
|---|---|---|---|---|
| **TH-01** | Cross-Tenant Data Access | Malicious API call from Tenant A requesting Tenant B records | `PolicyEngine` enforces strict caller/target equality. Cross-tenant calls raise `CrossTenantAccessViolation`. | `test_cross_tenant_read_strictly_prevented` (Passed) |
| **TH-02** | Telemetry Origin Spoofing | Telemetry packet embeds metadata claiming another tenant ID | Exporter IP and Domain ID are checked against trusted `TenantRegistry`. Mismatched claims raise `UntrustedTenantClaimViolation`. | `test_untrusted_telemetry_cannot_spoof_tenant` (Passed) |
| **TH-03** | Rogue Exporter Ingestion | Unauthenticated router transmits flows to collector | Exporter IP not registered in registry causes immediate drop and records `tenant_scope_violations`. | `test_unauthorized_exporter_ip_rejected` (Passed) |
| **TH-04** | Parser Denial-of-Service | Truncated packets, corrupted headers, huge declared lengths | Bounded packet sizes (65,507 bytes) and length-checked parsing with `CorruptedMessageError`. | `test_fuzzing_resilience_random_bytes` (Passed) |
| **TH-05** | Memory Exhaustion (DoS) | Attacker generates thousands of arbitrary template IDs | Templates are cached strictly per `(exporter_ip, observation_domain_id)`. Unregistered template IDs are safely skipped. | `test_missing_and_unknown_template_fault` (Passed) |
| **TH-06** | False Sense of Security | Attacker disables telemetry; operator assumes 0 threats | `CoverageTracker` explicitly classifies missing telemetry as `DEGRADED`, `UNKNOWN`, or `DEAD`. Emits warning banner. | `test_coverage_tracker_missing_telemetry_is_degraded_not_zero_threat` (Passed) |
| **TH-07** | Operator Abuse / Snoop | Platform admin attempts to read subscriber telemetry | `PLATFORM_ADMIN` role lacks `telemetry:read` permission. Only manages tenant metadata and audit trails. | `test_platform_admin_cannot_access_tenant_telemetry` (Passed) |
| **TH-08** | Subscriber Privacy Leak | Raw subscriber host IPs stored or exported | `TelemetryNormalizer` masks all subscriber host addresses to `/24` or `/48` subnets. | `test_normalizer_subscriber_ip_masking` (Passed) |
| **TH-09** | Credential Leakage | Hardcoded AWS keys or private keys in repository | `RepositorySecretScanner` runs in offline test suite and CI. | `test_repository_contains_no_secrets` (Passed) |

---

## 3. Residual Security Risks (Phase 1)
1. **Simulated vs Physical AWS IAM**: Level A tests verify Python source-code authorization logic and OpenTofu policy syntax. Physical cross-account AWS IAM trust boundaries remain unverified until paid cloud deployment is funded.
2. **UDP Ingress DDoS Protection**: In Phase 1, UDP rate limiting is modeled in memory. In production, AWS Shield Advanced or edge firewall scrubbing will be required to mitigate multi-gigabit volumetric UDP floods.
3. **Physical Hardware Authentication**: Router exporters currently authenticate via source IP and observation domain. Phase 2 should explore IPFIX over TLS (RFC 6615) with client certificates for cryptographically authenticated transport.
