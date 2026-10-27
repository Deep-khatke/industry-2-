# FCS-HMD Model Training & Lineage
## Training Procedures, Preprocessing, and Split Partitions

**Subsystem:** FCS-HMD  
**Architecture:** Version 1.2  
**Implementation:** `scripts/train_phase5_models.py`  
**Dataset Lineage:** Phase 2 locked datasets in `data/processed/`  

---

## 1. Dataset Partitions & Preprocessing

All Phase 5 models are trained strictly on Phase 2 validated artifacts to prevent data leakage:
- **Locked Splits:**
  - Training split (`train_split.parquet`): 345 flows
  - Validation split (`val_split.parquet`): 193 flows
  - Test split (`test_split.parquet`): 209 flows (184 Attack, 25 Benign)
- **Feature Schema:** Deployable 14-feature schema (`deployable_v1`):
  `L4_SRC_PORT`, `L4_DST_PORT`, `PROTOCOL`, `IN_BYTES`, `IN_PKTS`, `OUT_BYTES`, `OUT_PKTS`, `FLOW_DURATION_MILLISECONDS`, `TCP_FLAGS`, `CLIENT_TCP_FLAGS`, `SERVER_TCP_FLAGS`, `DURATION_IN`, `DURATION_OUT`, `MIN_TTL`.
- **Feature Scaling:** Training-only robust scaling via `preprocessor_state.json`:
  $$x_{\text{scaled}} = \frac{x - \text{center}}{\text{dispersion}}$$

---

## 2. Model Training Specifications

### A. Tenant Anomaly Detector (Isolation Forest)
- **Algorithm:** Scikit-Learn `IsolationForest(n_estimators=100, contamination=0.05, random_state=42)`
- **Data:** Trained exclusively on 106 benign flows from the 7 rural ISP partitions.
- **Calibration:** Raw decision function scores calibrated via sigmoid:
  $$p_{\text{anom}} = \frac{1}{1 + e^{10.0 \cdot \text{score}}}$$
- **Artifact:** `artifacts/candidate-models/isolationforest_anomaly_tenant/model.joblib`

### B. Tenant Anomaly Candidate (PyTorch Autoencoder)
- **Architecture:** PyTorch MLP Autoencoder ($9 \to 4 \to 9$ bottleneck).
- **Loss:** Mean Squared Error (Reconstruction Loss).
- **Calibration:** Reconstruction loss converted to probability:
  $$p_{\text{anom}} = \frac{1}{1 + e^{-(\text{MSE} - 0.01) / 0.02}}$$
- **Artifact:** `artifacts/candidate-models/autoencoder_anomaly/model.pt`

### C. DDoS Specialist Model
- **Algorithm:** LightGBM binary classifier (`n_estimators=50, max_depth=4, learning_rate=0.05`).
- **Data:** Trained on volumetric DDoS attack subsets with balanced benign negatives.
- **Performance:** PR-AUC: 0.9167, F1: 0.9254 on held-out validation.
- **Artifact:** `artifacts/candidate-models/lightgbm_ddos_specialist/model.txt`

### D. Scanning Specialist Model
- **Algorithm:** LightGBM binary classifier (`n_estimators=50, max_depth=4, learning_rate=0.05`).
- **Data:** Trained on port scan and reconnaissance probe subsets.
- **Performance:** PR-AUC: 0.8931, F1: 0.9195 on held-out validation.
- **Artifact:** `artifacts/candidate-models/lightgbm_scanning_specialist/model.txt`

### E. Botnet Specialist Model (Research Baseline)
- **Algorithm:** LightGBM binary classifier (`n_estimators=50, max_depth=4, learning_rate=0.05`).
- **Data:** Trained on research benchmark split.
- **Eligibility:** **`NOT_ELIGIBLE_FOR_PRODUCTION_DEPLOYMENT`**. Evaluated on benchmark dataset (PR-AUC: 0.9442), but excluded from production bundles because FlowEvent v1 lacks DNS entropy and packet jitter.
