# FCS-HMD Evidence Fusion Engine
## Deterministic Multi-Model Synthesis, Specialist Dominance & Uncertainty Handling

**Subsystem:** FCS-HMD  
**Architecture:** Version 1.2  
**Implementation:** `services/ml_training/src/fcs_ml/hmd/fusion.py`  

---

## 1. Fusion Philosophy: Determinism over Black Boxes

Rather than using an opaque neural network or uncalibrated stacking meta-model, `EvidenceFusionEngine` uses **deterministic Bayesian weighting** with explicit specialist dominance and rule risk floors. This ensures 100% auditability for SOC analysts, eliminates out-of-fold training-test prediction leakage, and enforces hard safety boundaries.

---

## 2. Multi-Stage Synthesis Algorithm

### Stage 1: Deterministic Behavioral Rule Floor
FCS detection rules (e.g. `FCS-R101` to `FCS-R104`) set an inviolable risk floor:
- Critical rule match $\implies$ Risk floor $\ge 0.95$
- High rule match $\implies$ Risk floor $\ge 0.85$
- Medium rule match $\implies$ Risk floor $\ge 0.65$

### Stage 2: Specialist Dominance
If a specialized attack classifier produces a high-confidence prediction:
$$p_{\text{specialist}} \ge 0.85$$
The specialist **dominates** the decision:
1. Threat category is assigned directly to the specialist's target vector (e.g. `DDoS` or `PortScan`).
2. Composite risk is calculated as:
   $$\text{Risk} = \max\left(p_{\text{specialist}}, 0.70 \cdot p_{\text{gen}} + 0.30 \cdot p_{\text{specialist}}\right)$$
3. The fusion method is tagged `SPECIALIST_DOMINANT`.

### Stage 3: Level 1 Weighted Synthesis
When specialists are not triggered or output moderate confidence ($< 0.85$):
$$\text{Risk}_{\text{base}} = w_{\text{gen}} \cdot p_{\text{gen}} + w_{\text{anom}} \cdot p_{\text{anom}}$$
Default weights: $w_{\text{gen}} = 0.50$, $w_{\text{anom}} = 0.25$, distributed across active models.

### Stage 4: Safety & Risk Floor Application
$$\text{Composite Risk} = \max\left(\text{Risk}_{\text{base}}, \text{Risk}_{\text{specialist}}, \text{Risk}_{\text{rule\_floor}}\right)$$

### Stage 5: Risk Tier Categorization
- $\text{Risk} \ge 0.85 \implies \textbf{CRITICAL}$
- $0.70 \le \text{Risk} < 0.85 \implies \textbf{HIGH}$
- $0.50 \le \text{Risk} < 0.70 \implies \textbf{MEDIUM}$
- $0.30 \le \text{Risk} < 0.50 \implies \textbf{LOW}$
- $\text{Risk} < 0.30 \implies \textbf{INFORMATIONAL}$

---

## 3. Explicit Margin Abstention & Missing Model Handling

- **Margin Abstention:** When an individual model probability falls within $|p - 0.50| < 0.05$, `ScoringStatus.ABSTAIN` is emitted, and `uncertainty_flag = True` is attached to the incident evidence.
- **Missing Models:** If an optional specialist is missing or timed out, it produces `ScoringStatus.MISSING` or `TIMEOUT`. The fusion engine falls back to Level 1 general screening and logs `FALLBACK_GENERAL_ONLY`. Missing models **never** hallucinate benign scores ($0.0$).
