# Federated Cyber Shield (FCS) v1.2 — Model Rollback & Emergency Fallback Procedures

## 1. When to Initiate Model Rollback

A model rollback or emergency fallback must be triggered when:
1. High false alarm rate is reported by tenant SOC teams following a federated round update.
2. Inference latency exceeds the SLO threshold (>50ms p95).
3. Cryptographic signature verification fails for an incoming model candidate.
4. Model weights exhibit numerical instability (NaN/Inf outputs).

---

## 2. Emergency Rollback Commands

### 2.1 Revert to Previous Validated Model Checkpoint
To point the model registry back to the previous verified model bundle:

```bash
# Update registry pointer to previous verified version
python -c "
from services.ml_training.registry import ModelRegistry
reg = ModelRegistry()
reg.activate_version('candidate_v1.1.0')
print('Activated previous stable candidate model.')
"
```

### 2.2 Force Immediate Fallback to Deterministic Rules Engine
If all machine learning artifacts are suspect, force immediate `RULES_ONLY` fallback:

```bash
# Set environment override
export FCS_DETECTION_MODE="RULES_ONLY"
# Or restart API with rules-only configuration
```

In `RULES_ONLY` mode, the deterministic heuristic rules engine (`FCS-R101` through `FCS-R104`) processes all incoming feature windows with zero reliance on tree weights or neural nets.
