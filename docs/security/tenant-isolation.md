# Federated Cyber Shield (FCS) v1.2 — Multi-Tenant Isolation Guarantees

## 1. Architectural Isolation Model

In telecommunications deployments, multiple independent ISPs or enterprise partitions share the same detection platform while maintaining complete data sovereignty.

FCS enforces a multi-tier tenant isolation boundary across seven simulated tenant cohorts (`ISP-A` through `ISP-G`):

```mermaid
flowchart TD
    UserRequest[Client Request with Bearer Token] --> TokenParser[JWT Context Parser]
    TokenParser --> ContextInjector[Inject tenant_id into Request State]
    
    subgraph DataBoundaries["Tenant Sovereignty Enforcement"]
        ContextInjector --> RouteGuard[Route Policy Guard (Reject cross-tenant IDOR)]
        RouteGuard --> QueryFilter["SQL Filter (WHERE tenant_id == :caller_tenant)"]
        QueryFilter --> Storage[Partitioned SQLite / In-Memory State]
    end

    subgraph DefenseBoundaries["Defensive Action Containment"]
        ContextInjector --> PolicyGuard[Tenant Response Policy Check]
        PolicyGuard --> ActionLedger[Tenant-Scoped Action Journal]
    end
```

---

## 2. Invariant Specifications

1. **Telemetry Ingestion Boundary**: Exporters are registered with fixed tenant ownership. An exporter claiming to send telemetry for `tenant-b` while authenticated as `tenant-a` is dropped immediately with an audit alert.
2. **Incident IDOR Protection**: Incident IDs are globally distinct. Any attempt by `tenant-b` to read, acknowledge, or mitigate an incident belonging to `tenant-a` returns HTTP `404 Not Found` or `403 Forbidden`.
3. **Response Policy Isolation**: Each tenant configures its own protected CIDR blocks (e.g., DNS root servers, critical upstream BGP gateways). Mitigations requested by one tenant cannot modify or override the policy of another tenant.
4. **Action Execution Sovereignty**: Actions issued in the Firewall Simulator are tagged with the issuing tenant and analyst identity. Simulator logs and active rules are partitioned by tenant.

---

## 3. Automated Verification Matrix

Verified under `tests/phase11/security/test_cross_tenant_isolation_matrix.py`:
- `test_cross_tenant_overview_isolation`: Tenant metrics and stats strictly separated.
- `test_cross_tenant_incident_ledger_isolation`: Incident queries cannot cross tenant boundaries.
- `test_cross_tenant_action_dispatch_denied`: Action creation across tenants rejected.
- `test_cross_tenant_response_policy_isolation`: Configuration updates contained strictly to caller tenant.
- `test_exporter_tenant_spoofing_prevented`: Telemetry spoofing rejected.
