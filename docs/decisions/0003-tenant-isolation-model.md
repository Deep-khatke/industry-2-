# Architecture Decision Record (ADR) 0003: Multi-Tenant Isolation and Telemetry Origin Binding

## Status
Accepted

## Context
Rural ISPs share the Federated Cyber Shield platform but must never have their raw subscriber traffic, network telemetry, or security incidents visible to competitor ISPs or unauthenticated platform operators.

## Decision
1. **Never Trust Untrusted Telemetry Claims**:
   - In IPFIX/NetFlow packets, exporter IP and observation domain ID are mapped against an authenticated, pre-registered `TenantRegistry`.
   - If incoming telemetry contains vendor metadata asserting a `tenant_id`, the normalizer strictly validates this claim against the trusted exporter configuration. Any mismatch raises `UntrustedTenantClaimViolation` and rejects the record.

2. **Platform Administrator Telemetry Denial**:
   - `PLATFORM_ADMIN` roles can manage tenant lifecycle and inspect platform health metrics.
   - Platform administrators are strictly **denied** access to raw tenant telemetry records (`Permission.TELEMETRY_READ`). Telemetry reading requires explicit `TENANT_ANALYST` or `TENANT_ADMIN` role within that specific tenant.

3. **Privacy-Preserving Network Masking**:
   - Raw subscriber IPv4 addresses are masked to `/24` subnets (and IPv6 to `/48`) during normalization.
   - Raw subscriber host IP addresses are never persisted or exported.

4. **Dedicated Cryptographic KMS Boundaries**:
   - In OpenTofu IaC, each tenant is provisioned a dedicated KMS customer-managed key (`fcs-kms-${tenant_id}`).
   - Cross-tenant data decryption is impossible without key policy authorization.

## Consequences
- Guaranteed zero-trust boundary, leak prevention, and full compliance with rural ISP privacy expectations.
