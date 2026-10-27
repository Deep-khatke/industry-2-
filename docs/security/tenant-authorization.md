# Federated Cyber Shield (FCS) v1.2 — Multi-Tenant Authorization Specification
## Multi-ISP Boundary Isolation, RBAC Matrix & Zero-Trust Access Control

**Status:** IMPLEMENTED & VERIFIED (Gate G01: PASS)  
**Tenancy Model:** Strict Partitioned Multi-Tenancy  
**Simulated ISPs:** 7 Tenants (`rural-isp-alpha` through `rural-isp-golf`)  

---

## 1. Multi-Tenant Isolation Architecture

Federated Cyber Shield is architected for shared multi-tenant ISP environments where strict logical isolation is mandatory. An ISP must never have visibility into or control over another ISP's telemetry, incidents, models, or firewall rules.

```text
       Incoming Client Request
                  │
                  ▼
       [FastAPI Auth Dependency]
                  │
                  ├─► Verify JWT Signature & Expiration
                  ├─► Extract Claims: user_id, role, tenant_id
                  │
                  ▼
       [Tenant Boundary Validator]
                  │
                  ├─► Check target_tenant_id == token.tenant_id
                  │   (PLATFORM_ADMIN may access all tenants)
                  │
                  ▼
      ┌───────────┴───────────┐
   MATCH                     MISMATCH
      │                         │
      ▼                         ▼
Execute Query with        RAISE 403 FORBIDDEN
WHERE tenant_id = ?       "Cross-tenant access denied"
```

### 1.1 Insecure Direct Object Reference (IDOR) Protection
- **No Client-Supplied Trust:** A client supplying a `tenant_id` query parameter or body payload is never trusted. If the supplied `tenant_id` does not match the token's `tenant_id`, the request is immediately rejected with `403 Forbidden`.
- **Database Partitioning:** Every query against `flow_events`, `feature_windows`, `incidents`, `recommendations`, `action_journal`, and `simulated_firewall_rules` includes `WHERE tenant_id = :tenant_id`.

---

## 2. Role-Based Access Control (RBAC) Matrix

| Endpoint Group | `READ_ONLY` | `SECURITY_ANALYST` | `SECURITY_RESPONDER` | `TENANT_ADMIN` | `PLATFORM_ADMIN` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **View Dashboard & Telemetry** (`GET /v1/overview`, `/v1/coverage`) | Allow | Allow | Allow | Allow | Allow |
| **Search & View Incidents** (`GET /v1/incidents`, `/{id}`) | Allow | Allow | Allow | Allow | Allow |
| **Update Incident Status** (`PATCH /v1/incidents/{id}`) | Deny (403) | Allow | Allow | Allow | Allow |
| **View Recommendations** (`GET /v1/incidents/{id}/recommendations`) | Allow | Allow | Allow | Allow | Allow |
| **Approve Defensive Actions** (`POST /v1/incidents/{id}/actions`) | Deny (403) | Deny (403) | Allow | Allow | Allow |
| **Roll Back Defensive Actions** (`POST /v1/actions/{id}/rollback`) | Deny (403) | Deny (403) | Allow | Allow | Allow |
| **Inspect Firewall Rules** (`GET /v1/firewall/rules`) | Allow | Allow | Allow | Allow | Allow |
| **Dev Replay Controls** (`POST /v1/dev/replay/*`) | Deny (403) | Deny (403) | Deny (403) | Allow | Allow |

---

## 3. Seeded Demonstration Accounts

For zero-cost development evaluation, demo accounts are seeded automatically at application startup. Each account is bound to a specific ISP tenant:

| Username | Role | Tenant ID | Default Password |
| :--- | :--- | :--- | :--- |
| `analyst_alpha` | `SECURITY_ANALYST` | `rural-isp-alpha` | `FcsDemo2026!` |
| `responder_alpha` | `SECURITY_RESPONDER` | `rural-isp-alpha` | `FcsDemo2026!` |
| `admin_alpha` | `TENANT_ADMIN` | `rural-isp-alpha` | `FcsDemo2026!` |
| `analyst_bravo` | `SECURITY_ANALYST` | `rural-isp-bravo` | `FcsDemo2026!` |
| `responder_bravo` | `SECURITY_RESPONDER` | `rural-isp-bravo` | `FcsDemo2026!` |
| `readonly_alpha` | `READ_ONLY` | `rural-isp-alpha` | `FcsDemo2026!` |
| `platform_admin` | `PLATFORM_ADMIN` | `fcs-global` | `FcsDemo2026!` |

> [!WARNING]
> Seeded demonstration accounts are restricted strictly to development environments. In production environments, authentication delegates to enterprise OpenID Connect / OAuth2 identity providers.

---

## 4. Verification Evidence (Gate G01)

Multi-tenant isolation and RBAC were verified through automated security tests in `tests/phase4-security/`:

1. `test_cross_tenant_idor_incident_access_denied`: Attempting to query `rural-isp-bravo` incidents using `rural-isp-alpha` token returned `403 Forbidden`.
2. `test_cross_tenant_action_approval_denied`: Attempting to execute an action on a `rural-isp-bravo` incident using `rural-isp-alpha` responder credentials returned `403 Forbidden`.
3. `test_read_only_role_cannot_modify_incidents`: Attempting to PATCH incident status using a `READ_ONLY` token returned `403 Forbidden`.
4. `test_security_analyst_cannot_approve_defensive_actions`: Attempting to execute a defensive mitigation action using `SECURITY_ANALYST` role returned `403 Forbidden`.
