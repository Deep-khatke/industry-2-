# FCS Phase 3 — Model Security, Integrity, and Adversarial Invariants

**Architecture Baseline:** Federated Cyber Shield v1.2  
**Component:** FCS-ML Security Architecture & Release Gate G06  
**Budget:** Strictly ₹0 / $0  

---

## 1. Threat Model for Machine Learning in FCS

Deploying machine learning models in multi-tenant cybersecurity environments exposes distinct vulnerability surfaces:
1. **Arbitrary Code Execution via Deserialization:** Untrusted model loading exploiting Python `pickle` vulnerabilities.
2. **Model Tampering & Supply-Chain Inversion:** Malicious modification of model weights on disk to suppress detection of specific adversarial attack traffic.
3. **Target / Label Leakage:** Accidental inclusion of ground-truth labels or ISP identifiers into training matrices, causing inflated offline scores and catastrophic online failure.
4. **Adversarial Input Injections:** Malformed inputs (NaN, $\pm\infty$, non-finite floating point numbers) designed to crash inference pipelines or trigger denial-of-service on telemetry ingestion.
5. **Unauthorized Network Action Execution:** ML detectors erroneously initiating firewall blocks or BGP route changes without human authorization.

---

## 2. Defensive Security Implementations

### A. Strict Prohibition of Arbitrary Pickles
Phase 3 mandates strictly non-executable model artifact representations:
- **LightGBM:** Native text model specification (`model.txt`) loaded via official C++ booster runtime, paired with sidecar JSON metadata.
- **PyTorch MLP:** Isolated PyTorch `state_dict` tensors (`model.pt`) loaded via `torch.load(..., weights_only=True)`, strictly prohibiting executable code injection.
- **Logistic Regression / Baseline:** Pure JSON representation (`model.json`) serializing scaler means, variances, weights, and intercepts.
- **Verification Rule:** Any attempt to load arbitrary executable `.pkl` or `.joblib` files is rejected by `MLSecurityValidator`.

### B. Cryptographic Model Manifests (Gate G06 Partial Evidence)
Every candidate model registered into `artifacts/candidate-models/` is sealed with a tamper-evident `ModelManifest`:
- Contains immutable SHA-256 digests of the combined model weights file and sidecar JSON metadata.
- Contains the exact canonical `feature_schema_digest` and `dataset_manifest_digest`.
- Before loading any model for inference, `CandidateModelRegistry.verify_model_artifact()` re-computes disk hashes. If any byte has been tampered with or corrupted, loading fails immediately with `MLSecurityError`.

### C. Runtime Input Invariants
`MLSecurityValidator.validate_inference_inputs()` enforces:
1. Expected feature dimensions strictly match `manifest.feature_names`.
2. Input matrices must not contain `NaN` or `Inf`.
3. Input columns must match the exact feature names and ordering defined in the verified `FeatureSpec`.

### D. Zero Network Actions Guarantee
In accordance with Architecture Gate G01 and response policies:
- The Phase 3 `InferenceEngine` produces scoring metadata only (`prediction`, `predicted_label`, `calibrated_probability`, `threshold_applied`, `is_uncertain`, `latency_microseconds`).
- Every result explicitly returns `network_action_executed = False`.
- The ML inference subsystem has zero network socket permissions, zero firewall integration, and zero credentials to execute cloud or router actions. Automated response is strictly reserved for future response policy governance phases.
