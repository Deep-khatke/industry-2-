# FCS Phase 3 — Evaluation Protocol and Metrics Specification

**Architecture Baseline:** Federated Cyber Shield v1.2  
**Component:** FCS-ML Evaluation Framework  
**Budget:** Strictly ₹0 / $0  

---

## 1. Principles of Evaluation

In cybersecurity intrusion detection, overall accuracy is notoriously deceptive due to massive class imbalance (where 90%+ of traffic in normal network operation is benign, or conversely in academic datasets where synthetic attacks dominate specific captures).

Phase 3 adheres to six scientific evaluation principles:
1. **Never optimize thresholds on test splits.**
2. **Never evaluate models on resampled or synthetic test distributions.**
3. **Always report Precision-Recall AUC (PR-AUC) alongside ROC-AUC.**
4. **Quantify the Operational False Positive Rate (FPR) at fixed recall floors.**
5. **Measure domain transfer generalization on untouched, source-disjoint holdouts.**
6. **Benchmark CPU latency, memory footprint, and throughput under realistic batch sizes.**

---

## 2. Metric Formulations

### Binary Intrusion Detection

| Metric | Formula | Purpose |
|---|---|---|
| **Precision** | $\frac{TP}{TP + FP}$ | Fraction of alerts that are genuine malicious attacks. High precision minimizes analyst fatigue. |
| **Recall (TPR)** | $\frac{TP}{TP + FN}$ | Fraction of actual attacks successfully detected by the model. |
| **F1 Score** | $2 \cdot \frac{Precision \cdot Recall}{Precision + Recall}$ | Harmonic mean balancing recall and precision. |
| **False Positive Rate (FPR)** | $\frac{FP}{FP + TN}$ | Fraction of normal traffic erroneously flagged as attack. Critical for ISP SLA adherence. |
| **PR-AUC** | $\int Precision(R) dR$ | Area under the precision-recall curve. Superior to ROC-AUC under severe class skew. |
| **ROC-AUC** | $\int TPR(FPR) dFPR$ | Area under receiver operating characteristic. Measures ranking separability across thresholds. |
| **Balanced Accuracy** | $\frac{1}{2} (TPR + TNR)$ | Unweighted average recall across positive and negative classes. |
| **Matthews Correlation (MCC)** | $\frac{TP \cdot TN - FP \cdot FN}{\sqrt{(TP+FP)(TP+FN)(TN+FP)(TN+FN)}}$ | Balanced correlation coefficient between prediction and truth. |

### Probability Calibration & Reliability

- **Expected Calibration Error (ECE):**
  $$ECE = \sum_{m=1}^{M} \frac{|B_m|}{N} \left| acc(B_m) - conf(B_m) \right|$$
  Measures the difference between predicted confidence and observed empirical accuracy across $M=10$ equal-width probability bins.
- **Brier Score:**
  $$BS = \frac{1}{N} \sum_{i=1}^{N} (p_i - y_i)^2$$
  Mean squared error between predicted probability $p_i$ and true binary label $y_i$.

---

## 3. Threshold Selection Protocol

Default thresholds of 0.5 are rarely optimal for high-stakes cybersecurity telemetry. Phase 3 implements `ThresholdOptimizer` operating exclusively on the validation split:

1. **Max F1 Strategy (`max_f1`):**
   - Scans candidate thresholds $\tau \in [0.01, 0.99]$ with step size 0.01.
   - Selects $\tau^* = \arg\max_\tau F_1(\tau; X_{val}, y_{val})$.
   - Freezes $\tau^*$ and embeds it into `ModelManifest.validation_threshold`.

2. **Target False Positive Rate Strategy (`target_fpr`):**
   - Given an operational FPR budget $\alpha$ (e.g., $\alpha = 0.01$ or 1% false alert rate), finds:
     $$\tau^* = \min \{ \tau \mid FPR(\tau; X_{val}, y_{val}) \le \alpha \}$$
   - Maximizes recall subject to not exceeding the false alarm budget.

3. **Abstention & Uncertainty Flagging:**
   - If calibrated probability satisfies $|p - \tau| < \epsilon_{uncertainty}$ (or in multiclass if $\max_k p_k < \tau_{uncertainty}$), prediction is flagged with `is_uncertain = True` and status `ABSTAIN` / `REVIEW_REQUIRED`.

---

## 4. Probability Calibration

Many algorithms (such as tree ensembles and unregularized neural networks) output uncalibrated scores that do not reflect true statistical probabilities. Phase 3 supports:
- **Platt Scaling (Sigmoid):** Fits a logistic regression mapping $z \mapsto \frac{1}{1 + \exp(A z + B)}$ on validation scores.
- **Isotonic Regression:** Fits a non-parametric piecewise monotonic function on validation scores when sufficient calibration samples ($N \ge 1000$) exist.

Both methods are verified via before-and-after ECE reporting.

---

## 5. Domain Generalization & Cross-Source Evaluation (E3-06)

To detect dataset-specific shortcuts (e.g., port numbers or TTL artifacts that correlate with attacks in one lab capture but fail in another), the evaluation protocol tests models on the independent holdout partition:
- **Training Source Lineage:** NF-UQ-NIDS-v2 composite training split.
- **Untouched Holdout Source:** Independent source partition (e.g. `NF-ToN-IoT-v2` or `NF-BoT-IoT-v2`).
- **Evaluation:** Evaluates detection degradation, class recall shifts, and false positive spikes under unseen network topologies.

---

## 6. Operational Resource Benchmarking (E3-08)

To ensure feasibility on rural ISP edge nodes and low-cost CPU servers:
- **Batch Sizes Tested:** 1 (streaming single-flow), 10, 50, 100, 500 flows.
- **Latency Percentiles:** p50 (median), p95 (tail SLA), p99 (worst-case).
- **Throughput:** Measured in flows scored per second under warm and cold cache conditions.
- **Hard Threshold:** Single-flow scoring latency must remain strictly below 50 milliseconds on standard CPU cores.
