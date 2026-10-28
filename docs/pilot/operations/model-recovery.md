# Model Recovery and Rollback Procedures

## 1. Trigger Conditions for Model Rollback
A model rollback must be executed within $\le 5$ minutes if any of the following occur:
1. High false alert spike ($> 5$ false grouped alerts in a single 24-hour observation window).
2. Inference latency breach ($p95 > 5.0\text{s}$ or $p99 > 15.0\text{s}$).
3. Corrupted or unverified model manifest detected.
4. Tampered gradient share detected during federated learning update.

## 2. Model Rollback Execution
1. Issue model rollback instruction via API or CLI:
   ```bash
   python -c "from fcs_ml.registry import ModelRegistry; ModelRegistry().rollback_to_previous_verified_model('rural-isp-alpha')"
   ```
2. The system deactivates the candidate model and restores the previously verified signed bundle (`1.2.0-hmd-verified`).
3. Evidence fusion falls back to deterministic rule heuristics during the $< 100\text{ms}$ transition interval.
4. The incident engine logs a `MODEL_ROLLBACK_COMPLETED` audit event.
