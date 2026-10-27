# FCS-HMD Security Controls & Safety Boundaries
## Multi-Tenancy Isolation, Model Artifact Security, and Safety Invariants

**Subsystem:** FCS-HMD  
**Architecture:** Version 1.2  
**Implementation:** `services/api/src/fcs_api/routes/detection.py` & `services/ml_training/src/fcs_ml/hmd/`  

---

## 1. Multi-Tenant Anomaly Model Isolation

1. **Partitioned File Storage:**
   Tenant anomaly models are stored in isolated per-tenant paths:
   `artifacts/candidate-models/tenants/{tenant_id}/`
2. **Access Control (RBAC):**
   Endpoints verify that the caller's JWT `tenant_id` matches the target resource. Cross-tenant access queries (e.g. `rural-isp-alpha` querying `rural-isp-bravo`'s model) are immediately rejected with **HTTP 403 Forbidden**.
3. **No Cross-Tenant Contamination:**
   Anomaly models are trained strictly on local benign traffic slices. Models are never merged, averaged, or centralized across tenants.

---

## 2. Model Artifact Integrity & Anti-Tampering

1. **SHA-256 Checksums:**
   Every candidate model file (`model.txt`, `model.joblib`, `model.pt`) has its SHA-256 hash locked in `model_manifest.json` and `DetectionBundle`.
2. **Safe Serving Formats:**
   - LightGBM models serve via standard text boosters (`model.txt`), preventing arbitrary code execution.
   - PyTorch models serve via pure state dicts (`model.pt`).
   - Untrusted pickle loading from external network endpoints is prohibited.
3. **Authorized Activation Only:**
   Bundle activation and rollback require authenticated users with `PLATFORM_ADMIN` or `TENANT_ADMIN` roles. Non-admin users attempting bundle mutation receive HTTP 403.

---

## 3. Strict Safety Invariant: Manual Mode Permanence

> [!CAUTION]
> **No AI Model Can Directly Execute a Network Action:**
> - In `ModelScore`, the invariant `network_action_executed = False` is statically sealed.
> - In `CompositeThreatEvidence`, `network_action_executed = False` is strictly enforced.
> - The automated mitigation engine (`AUTO` mode) is permanently disabled.
> - All firewall modifications, route dampening, and traffic shaping actions require explicit, manual authorization by a human SOC operator via authenticated `POST /v1/response/execute`.
