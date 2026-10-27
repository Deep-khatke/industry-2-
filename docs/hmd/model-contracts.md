# FCS-HMD Model Contracts & Data Specifications
## Standardized ModelScore v1 Contract & DetectionBundle Interface

**Subsystem:** FCS-HMD  
**Architecture:** Version 1.2  
**Specification:** `packages/contracts/model_score.py` & `services/ml_training/src/fcs_ml/hmd/bundle.py`  

---

## 1. ModelScore v1 Contract

Every model in the FCS-HMD hierarchy outputs an immutable `ModelScore` dataclass.

### Schema Fields

| Field | Type | Constraint | Description |
|---|---|---|---|
| `model_id` | `str` | Required | Registered identifier of the model (e.g. `lightgbm_ddos_specialist`) |
| `model_type` | `ModelType` | Enum | `GENERAL_DETECTOR`, `ANOMALY_DETECTOR`, `DDOS_SPECIALIST`, `SCANNING_SPECIALIST`, `BOTNET_SPECIALIST`, `RULE_ENGINE` |
| `version` | `str` | SemVer | Model artifact version (e.g. `1.2.0`) |
| `raw_score` | `float` | Arbitrary | Uncalibrated booster margin, reconstruction error, or tree path distance |
| `calibrated_probability` | `float` | $[0.0, 1.0]$ | Model-calibrated probability of malicious intent |
| `confidence` | `float` | $[0.0, 1.0]$ | Epistemic confidence score |
| `threshold_applied` | `float` | $[0.0, 1.0]$ | Operating decision threshold applied |
| `prediction` | `int` | $\{0, 1, -1\}$ | 0 = Benign/Normal, 1 = Threat/Anomaly, -1 = Unscored/Error |
| `predicted_label` | `str` | Non-empty | Semantic label (`Benign`, `Attack`, `DDoS`, `PortScan`, `ERROR`) |
| `is_uncertain` | `bool` | Boolean | True if calibrated probability falls within the margin $[th - 0.05, th + 0.05]$ |
| `status` | `ScoringStatus` | Enum | `SCORED`, `ABSTAIN`, `UNCERTAIN`, `TIMEOUT`, `MISSING`, `ERROR`, `BYPASSED` |
| `latency_microseconds` | `float` | $\ge 0.0$ | Measured CPU execution latency |
| `features_used` | `list[str]` | List | Names of features consumed |
| `reason_codes` | `list[str]` | List | Explainability reason codes or feature contributions |
| `tenant_context` | `str` | String | Tenant partition scope (`rural-isp-alpha`, etc.) |
| `timestamp` | `str` | ISO 8601 | UTC generation timestamp |
| `network_action_executed` | `bool` | **Always False** | **Safety invariant**: ML models only emit evidence; response execution requires human authorization |

---

## 2. DetectionBundle Specification

A `DetectionBundle` binds constituent model artifacts by SHA-256 digest to prevent unauthorized tampering.

```json
{
  "bundle_id": "fcs-hmd-bundle-v1",
  "version": "1.2.0",
  "general_model_id": "lightgbm_deployable_subset",
  "anomaly_model_id": "isolationforest_anomaly_tenant",
  "specialist_model_ids": [
    "lightgbm_ddos_specialist",
    "lightgbm_scanning_specialist"
  ],
  "model_hashes": {
    "lightgbm_deployable_subset": "f776a93db005a242c329d183a04f83899aaaaf72972ed884525bacda368a8f58",
    "isolationforest_anomaly_tenant": "93efc8df38b5b2e942d4762c9ac99cf02752cd9edeb7fe709c356e98d9ca1b8f",
    "lightgbm_ddos_specialist": "a43bbb2c9930e43b9375901ad1a9c033f2b14c5168a06447f7ee2a6eb16fc0dd",
    "lightgbm_scanning_specialist": "db34b856925c81762b348786ab0834e03d7b3a67385cd0d9850b5843d83c656f"
  },
  "bundle_digest": "2bd8454c761cc75af262f25b11fa6031385c22649e6ad51c7e1eb2a88a40e493",
  "authorized_by": "security_admin",
  "status": "ACTIVE"
}
```

### Bundle Integrity Verification
Before activation, `BundleValidator.validate()`:
1. Re-computes SHA-256 checksum of every model file in the registry.
2. Compares against both the registry manifest and the bundle's `model_hashes`.
3. Verifies deterministic canonical digest `bundle_digest`.
4. Rejects tampered or unverified artifacts with an explicit error list.
