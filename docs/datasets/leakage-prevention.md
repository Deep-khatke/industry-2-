# Federated Cyber Shield — Data Leakage Prevention Architecture

**Architecture Baseline:** FCS v1.2  
**Component:** FCS-UDIP Leakage Prevention, Splitting & Preprocessing Isolation  
**Specification Version:** 1.2.0  

---

## 1. Threat Model for Dataset Leakage

In cybersecurity ML research, models frequently report >99.9% accuracy on benchmark test sets but collapse to near-zero utility in production environments. FCS-UDIP systematically addresses the 6 root causes of dataset leakage:

```
+-----------------------------------------------------------------------------+
|                           DATA LEAKAGE VECTORS                              |
+-----------------------------------------------------------------------------+
|  1. Exact Record Leakage:       Identical flow rows in train and test       |
|  2. Group / Host Leakage:       Same victim IP / subnet in train and test    |
|  3. Preprocessing Leakage:      Fitting scalers/imputers across all splits  |
|  4. Temporal Inversion:         Training on future flows to predict past    |
|  5. Provenance Shortcut:        Model memorizes dataset_source indicator    |
|  6. Domain Inbreeding:          Evaluating on testbed identical to training |
+-----------------------------------------------------------------------------+
```

---

## 2. Leakage Safeguard Implementation

### 2.1 Group-Aware Host & Subnet Isolation
- **Mechanism:** Flows originating from or destined to a specific host or `/24` subnet must not be split randomly across train, validation, and test sets.
- **Implementation:** `DatasetSplitter` hashes group identifiers (`SRC_PREFIX_MASKED` / `DST_PREFIX_MASKED`) and assigns all records for a given subnet exclusively to one split partition.
- **Verification:** An explicit post-split set intersection assertion checks `len(train_groups.intersection(test_groups)) == 0`. If any shared group is detected, a `LeakageDetectedError` is raised.

### 2.2 Independent Original-Source Holdout
- **Mechanism:** In addition to random/group splitting within domains, the pipeline permanently isolates an entire independent testbed domain (e.g., `NF-ToN-IoT-v2`) from all training operations.
- **Outcome:** The held-out source serves as a rigorous zero-shot domain generalization evaluation set in Phase 3.

### 2.3 Strict Training-Only Preprocessing
- **Rule:** The fit step must consume only the training partition:
  $$\text{Preprocessor.fit}(D_{\text{train}})$$
- **Enforcement:**
  ```python
  preprocessor = TrainingOnlyPreprocessor()
  preprocessor.fit(train_df)  # Computes medians, bounds, and normalizers on train only

  train_prep = preprocessor.transform(train_df)
  val_prep = preprocessor.transform(val_df)      # Transformed using train parameters
  test_prep = preprocessor.transform(test_df)    # Transformed using train parameters
  ```
- Any scaling, quantile clipping, or categorical mapping fitted on validation or test data is structurally prevented. Preprocessor parameters are frozen and exported to `preprocessor_state.json`.

### 2.4 Subnet Privacy Masking
- Raw IPv4 addresses (`IPV4_SRC_ADDR`, `IPV4_DST_ADDR`) are transformed to `/24` network prefixes (`SRC_PREFIX_MASKED`, `DST_PREFIX_MASKED`).
- Raw IPs are dropped from the training feature matrix $X$ to prevent classifiers from simply memorizing victim and attacker IP addresses from the synthetic capture testbeds.

### 2.5 Deduplication & Overlap Auditing
- **Exact Duplicates:** Records with identical 43 NetFlow features are detected and deduplicated via SHA-256 row fingerprints.
- **Cross-Source Overlap Detection:** `DatasetDeduplicator` computes cross-source overlap matrices to verify that parent datasets do not contaminate composite benchmarks.
