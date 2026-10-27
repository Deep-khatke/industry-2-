# Federated Cyber Shield — Dataset Licensing & Governance

**Architecture Baseline:** FCS v1.2  
**Component:** FCS-UDIP Licensing & Provenance Governance  
**Budget Classification:** ₹0 / $0 Strict Open-Source Compliance  

---

## 1. Zero-Cost & Legal Governance Mandate

Federated Cyber Shield strictly prohibits the acquisition or ingestion of commercial, paid, or closed-source network traffic datasets. All data engineering pipelines and model training artifacts must originate exclusively from free, publicly authorized academic sources.

---

## 2. Dataset Terms of Use & Licensing Summary

| Dataset Identifier | Author / Institution | License Classification | Commercial Use Allowed | Attribution Required |
| :--- | :--- | :--- | :--- | :--- |
| **NF-UQ-NIDS-v2** | Marius Portmann Lab, Univ. of Queensland | Academic Research Only (Free) | **NO — Strictly Prohibited** | **YES — Sarhan et al. (2021)** |
| **NF-UNSW-NB15-v2** | UNSW Canberra Cyber Range | Academic Research Only (Free) | **NO — Strictly Prohibited** | **YES — Moustafa & Slay (2015)** |
| **NF-CSE-CIC-IDS2018-v2** | CSE & CIC (Univ. of New Brunswick) | Academic Research Only (Free) | **NO — Strictly Prohibited** | **YES — Sharafaldin et al. (2018)** |
| **NF-BoT-IoT-v2** | UNSW Canberra Cyber Range | Academic Research Only (Free) | **NO — Strictly Prohibited** | **YES — Koroniotis et al. (2019)** |
| **NF-ToN-IoT-v2** | UNSW Canberra Cyber Range | Academic Research Only (Free) | **NO — Strictly Prohibited** | **YES — Alsaedi et al. (2020)** |
| **CIC-DDoS2019** | CIC (Univ. of New Brunswick) | Academic Research Only (Free) | **NO — Strictly Prohibited** | **YES — Sharafaldin et al. (2019)** |

---

## 3. Machine-Readable License Enforcement

FCS-UDIP integrates programmatic licensing checks via `DatasetRegistry.verify_licensing()`:

```python
registry = DatasetRegistry("configs/datasets/sources.yaml")

# Verify license permits academic research
is_valid, reason = registry.verify_licensing("NF-UQ-NIDS-v2", intended_use="RESEARCH")
assert is_valid is True

# Block prohibited commercial use
is_valid, reason = registry.verify_licensing("NF-UQ-NIDS-v2", intended_use="COMMERCIAL")
assert is_valid is False
# Result: "COMMERCIAL_USE_BLOCKED: Dataset 'NF-UQ-NIDS-v2' license prohibits commercial exploitation."
```

### Prohibited Actions
1. **No Commercial Cloud Uploads:** Raw benchmark files must never be uploaded to public S3 buckets, BigQuery, or commercial data lakes.
2. **No Repository Commits of Raw Benchmarks:** The `.gitignore` file enforces that all files in `data/raw/`, `data/staging/`, and raw `*.parquet` / `*.csv.gz` files are strictly excluded from git.
3. **Synthetic Fixtures Only in CI:** Only synthetic, non-PII test fixtures (`data/synthetic-fixtures/`) may be committed to version control for CI testing.

---

## 4. Citation Requirements

Any publication or experimental report derived from FCS Phase 2 must cite:

```bibtex
@article{sarhan2021standard,
  title={Towards a Standard Feature Set for Network Intrusion Detection System Datasets},
  author={Sarhan, Mohanad and Layeghy, Siamak and Portmann, Marius},
  journal={Mobile Networks and Applications},
  year={2021},
  publisher={Springer}
}
```
