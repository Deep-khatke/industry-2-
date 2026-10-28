# Manual Defensive Response Policy Engine & Safety Controls

## 1. Manual Response Exclusivity
In FCS v1.2 Phase 9, **Manual Response is the ONLY authorized response mode**.
Automatic Response (AUTO) is permanently disabled (`auto_response_enabled = False`). No ML prediction or model confidence score alone may ever dispatch commands to a network router or firewall.

## 2. Response Dual-Authorization Workflow
```
[ Telemetry Ingestion ]
         v
[ FCS-HMD Threat Detection (Anomaly >= 0.70) ]
         v
[ Candidate Incident Created (Advisory Only) ]
         v
[ Tier-1 SOC Analyst Triage ]
   - Inspects evidence, window features, source IP
   - Submits disposition (TRUE_POSITIVE)
   - Recommends defensive action (TEMPORARY_BLOCK)
         v
[ Tier-2 Security Responder Review ]
   - Validates target against protected infrastructure
   - Verifies tenant scoping & duration bounds (60s to 3600s)
   - Executes explicit cryptographic approval
         v
[ Execution Engine: FIREWALL_SIMULATOR_DEFAULT ]
   - Applies rule to local simulated firewall state
   - Reads back state to verify execution
   - Commits record to append-only action journal
   - Automatically expires / rolls back rule upon TTL expiry
```

## 3. Protected Infrastructure Allowlists
Actions targeting the following categories are unconditionally rejected by `ResponsePolicyEngine`:
- DNS Root & Public Resolvers (`1.1.1.1`, `8.8.8.8`, `8.8.4.4`, `9.9.9.9`, `208.67.222.222`).
- Management Gateway IPs (`10.0.0.1`, `10.0.1.1`, `192.168.1.1`, `192.168.0.1`, `10.255.255.1`).
- Shared carrier-grade NAT (CGNAT) pools without port-level scoping.
- Emergency communications infrastructure.

## 4. Idempotency & Reversibility
- Every manual action request requires a unique `idempotency_key`. Duplicate requests return the cached action outcome.
- Permanent blocking is strictly prohibited: duration must satisfy $60 \le t \le 3600$ seconds.
- Every rule must support instantaneous manual or scheduled automated rollback.
