# Federated Cyber Shield (FCS) v1.2 — Manual Response Policy Specification
## Human-in-the-Loop Defensive Response Guardrails & Safety Policy

**Status:** ENFORCED & VERIFIED  
**Response Mode:** Strict MANUAL Mode  
**Autonomous Mode (AUTO):** DISABLED (G13 Release Gate: NOT_APPLICABLE / NOT_ENABLED)  
**Safety Invariant:** Zero Real Network Modifications (`network_action_executed = False`)  

---

## 1. Core Principles

Federated Cyber Shield enforces a strict, defense-in-depth safety architecture for all threat mitigation workflows:

1. **Model Output Is Evidence, Not Authority:** Machine learning inference predictions and rule matches serve strictly as investigative context and threat evidence. An ML prediction alone can never trigger or authorize a network configuration change.
2. **Mandatory Human-in-the-Loop:** In Phase 4, network defensive actions require explicit authorization by an authenticated human administrator holding `SECURITY_RESPONDER` or `TENANT_ADMIN` privileges.
3. **Autonomous Mode (`AUTO`) Hard Disabled:** Any configuration or API request attempting to enable autonomous firewall execution is rejected with `403 Forbidden` and logged as a policy violation.
4. **Isolated Software Simulation:** All defensive actions in Phase 4 execute within an isolated, in-process software firewall simulator. No physical routers, switches, firewalls, or production interfaces are ever contacted.
5. **Auditable & Reversible:** Every response attempt produces an immutable action journal record, with verifiable rule IDs and one-click rollback capability.

---

## 2. Policy Enforcement Matrix

| Check | Constraint | Enforcement Mechanism | Failure Response |
| :--- | :--- | :--- | :--- |
| **Authentication** | Valid Bearer JWT Token | `get_current_user` dependency | `401 Unauthorized` |
| **RBAC Authority** | `SECURITY_RESPONDER` or `TENANT_ADMIN` | [ResponsePolicyEngine.execute_manual_action](file:///c:/college/industry%202/services/api/src/fcs_api/response/engine.py) | `403 Forbidden` |
| **Tenant Ownership** | Incident must belong to user's assigned tenant | Tenant boundary cross-check | `403 Forbidden` |
| **Action Type** | `TEMPORARY_BLOCK`, `RATE_LIMIT`, `DEEP_INSPECTION` | Allowed action type whitelist | `400 Bad Request` |
| **Protected Targets** | Prohibit management IPs (`10.0.0.1`, `10.0.0.2`, `192.168.1.1`, `127.0.0.1`, `1.1.1.1`) | Exact IP & CIDR match validation | `400 Bad Request` |
| **Duration Bounds** | Clamped between 60s and 86,400s (24 hours) | Range assertion | `400 Bad Request` |
| **Idempotency** | Duplicate key with conflicting parameters rejected | SHA-256 parameter fingerprint match | `400 Bad Request` |
| **Execution State** | Simulator must verify rule exists in rule table | Read-back verification in [FirewallSimulator](file:///c:/college/industry%202/services/api/src/fcs_api/firewall/simulator.py) | `500 Server Error` (State UNCERTAIN) |

---

## 3. Workflow Specification

```text
Threat Detection Engine
        │
        ▼ (Generates Incident + Recommendations)
Incident Database
        │
        ▼ (Analyst inspects SOC Dashboard)
Administrator Review Modal
        │
        ▼ (Clicks "Authorize Mitigation")
POST /v1/incidents/{id}/actions
        │
        ├─► [Check 1] Validate JWT Signature & Tenant ID
        ├─► [Check 2] Assert User Role in {RESPONDER, ADMIN}
        ├─► [Check 3] Verify Incident Tenant Matches User Tenant
        ├─► [Check 4] Verify Target IP NOT in Protected Targets Allowlist
        ├─► [Check 5] Verify Action Duration Between 60s and 86,400s
        ├─► [Check 6] Check Idempotency Key in Action Journal
        │
        ▼ (Preconditions Passed)
INSERT action_journal (Status: PENDING)
        │
        ▼
FirewallSimulator.apply_rule()
        │
        ├─► INSERT simulated_firewall_rules (Status: ACTIVE, expires_at_utc)
        └─► Read-back rule table to verify rule insertion
        │
        ▼
UPDATE action_journal (Status: VERIFIED, simulated_rule_id)
UPDATE incidents (Status: MITIGATED)
        │
        ▼
Return 200 OK + Safety Disclaimer to Dashboard
```

---

## 4. Protected Targets Allowlist

To prevent denial-of-service against critical network operations, the following targets are strictly blocked from defensive action execution:

```python
PROTECTED_TARGETS = {
    "10.0.0.1",       # ISP Core Gateway
    "10.0.0.2",       # ISP Internal DNS / BGP Route Reflector
    "192.168.1.1",    # Local CPE Management Interface
    "127.0.0.1",      # Loopback
    "1.1.1.1",        # Public Upstream Resolver
    "8.8.8.8",        # Public Upstream Resolver
}
```

Any attempt to apply a block or rate limit against these IP addresses is rejected with:
`Protected target '10.0.0.1' cannot be blocked or rate-limited by policy.`

---

## 5. Software Firewall Simulator Verification & Rollback

### Rule Lifecycle
1. **Rule Creation:** Generates a deterministic rule identifier: `RULE-<hash>` with status `ACTIVE`.
2. **Verification Loop:** Immediately queries `simulated_firewall_rules` for the inserted rule. If the rule cannot be verified in the table, the action status is marked `UNCERTAIN` and the transaction aborts.
3. **Rollback Execution:**
   - Security Responders can invoke `POST /v1/actions/{action_id}/rollback`.
   - The simulator sets rule status to `REVOKED`.
   - The action journal status transitions to `ROLLED_BACK`.
   - A verification read-back ensures the rule is no longer `ACTIVE`.
4. **Time-To-Live (TTL) Expiry:**
   - Active rules include an `expires_at_utc` timestamp.
   - When queried, rules past their expiration timestamp are dynamically flagged as `EXPIRED`.

### Clear Safety Disclaimer
Every simulated defensive action record returned by the backend includes the immutable banner:
> **"Simulated defensive action — no real network device modified."**
