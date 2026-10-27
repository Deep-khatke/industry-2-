# Federated Cyber Shield — Dataset Catalog (FCS-UDIP)

**Architecture Baseline:** FCS v1.2  
**Component:** Unified Dataset Intelligence Pipeline (FCS-UDIP)  
**Budget Classification:** ₹0 / $0 Free Academic Research Only  

---

## 1. Executive Overview

The **Unified Dataset Intelligence Pipeline (FCS-UDIP)** provides an auditable, reproducible, and leakage-safe dataset engineering foundation for Federated Cyber Shield. To ensure zero licensing costs, rigorous peer-reviewed methodology, and cross-dataset evaluation capabilities, FCS-UDIP designates **NF-UQ-NIDS-v2** as its primary benchmark dataset, complemented by isolated parent datasets for independent source holdout and domain shift analysis.

---

## 2. Authoritative Dataset Registry

### 2.1 Primary Benchmark Dataset: NF-UQ-NIDS-v2

| Attribute | Specification |
| :--- | :--- |
| **Dataset Identifier** | `NF-UQ-NIDS-v2` |
| **Full Title** | NetFlow v2 University of Queensland Network Intrusion Detection System Dataset |
| **Official Research Portal** | [UQ eSpace / Data Repository](https://rdm.uq.edu.au/files/e2412450-ef9c-11ed-827d-e762de186848) |
| **Author / Lab Page** | [Prof. Marius Portmann Lab, University of Queensland](https://staff.itee.uq.edu.au/marius/NIDS_datasets/) |
| **Publication Citation** | M. Sarhan, S. Layeghy, and M. Portmann, *"Towards a Standard Feature Set for Network Intrusion Detection System Datasets"*, Mobile Networks and Applications, 2021 / arXiv:2101.11315. |
| **License Type** | Academic Research Only (Non-Commercial, Attribution Required) |
| **Format** | Compressed CSV / Parquet (NetFlow v2 extended schema) |
| **Total Benchmark Volume** | ~75,987,976 flow records across 4 constituent testbed domains |
| **Feature Dimension** | Exactly 43 canonical NetFlow v2 features extracted via nProbe |
| **Target Distribution** | Binary (`0` = Benign, `1` = Attack) and Multiclass Attack taxonomy |

#### Lineage & Composition
NF-UQ-NIDS-v2 is an authoritative composite benchmark synthesized from four distinct network capture testbeds:
1. **NF-UNSW-NB15-v2** (~2.39M flows) — Synthetic modern attacks and contemporary normal background traffic (Australian Centre for Cyber Security).
2. **NF-CSE-CIC-IDS2018-v2** (~18.89M flows) — AWS cloud testbed with multi-day enterprise attack campaigns (Communications Security Establishment & Canadian Institute for Cybersecurity).
3. **NF-BoT-IoT-v2** (~37.76M flows) — IoT testbed with massive DoS/DDoS, reconnaissance, and theft traffic (Cyber Range Lab, UNSW Canberra).
4. **NF-ToN-IoT-v2** (~16.94M flows) — Heterogeneous Industry 4.0 / IoT testbed spanning edge and cloud layers (UNSW Canberra).

> [!CRITICAL]
> **Parent Dataset Overlap Rule:** NF-UQ-NIDS-v2 already contains the normalized records of its four parent datasets. The pipeline strictly forbids appending parent datasets to NF-UQ-NIDS-v2. Doing so causes cross-dataset record duplication and invalidates empirical claims. Parent datasets are reserved strictly for independent source holdout evaluation and domain shift studies.

---

### 2.2 Parent & Source Holdout Datasets

#### NF-UNSW-NB15-v2
- **Source:** UNSW Canberra Cyber Range
- **Role in FCS:** Training/evaluation domain; provides Exploits, Fuzzers, Generic, Analysis, and Backdoors.
- **Lineage Hash Check:** Verified against official UQ release checksums.

#### NF-CSE-CIC-IDS2018-v2
- **Source:** AWS cloud simulation with 7 attack profiles
- **Role in FCS:** Cloud infrastructure threat domain; provides Infiltration, Web Attacks, Brute Force, and DoS/DDoS.

#### NF-BoT-IoT-v2
- **Source:** Node-RED simulated IoT smart home testbed
- **Role in FCS:** IoT device threat domain; high-volume DoS, DDoS, Service Scan, and OS Fingerprinting.

#### NF-ToN-IoT-v2
- **Source:** Telemetry from IoT/IIoT testbeds (Modbus, MQTT, Linux/Windows endpoints)
- **Role in FCS:** **Primary Independent Source Holdout Domain** in default split policy; provides completely out-of-domain evaluation for Phase 3 models.

---

### 2.3 Additional & Incompatible Dataset Handling

#### CIC-DDoS2019
- **Official Portal:** [UNB Canadian Institute for Cybersecurity](https://www.unb.ca/cic/datasets/ddos-2019.html)
- **Policy:** **Quarantined from Unified NetFlow Benchmark**. CIC-DDoS2019 uses an 80+ bidirectional CICFlowMeter feature schema with incompatible feature definitions, microsecond duration units, and non-overlapping statistical calculations. It may only be utilized in an isolated specialist benchmark after establishing verified transforms.

#### NetFlow v3 (53-Feature Family)
- **Policy:** **Strictly Segregated**. NetFlow v3 introduces 10 additional application-layer DPI features not present in NetFlow v2. Merging v2 and v3 rows into a single table without an explicitly validated common projection causes column null inflation and target distribution skew. The `SchemaInspector` rejects any attempt to merge v3 records into v2 pipelines.

---

## 3. Storage Hierarchy & Directory Structure

To maintain zero cloud cost and absolute local reproducibility, datasets reside in a strictly bounded local hierarchy excluded from git:

```
data/
├── raw/                      # Immutable raw source archives and CSVs
├── staging/                  # Intermediate chunked and typed Parquet conversions
├── processed/
│   ├── clean/                # Quality-accepted canonical Parquet datasets
│   ├── quarantine/           # Segregated corrupt/out-of-bounds records
│   ├── splits/               # Leakage-isolated train / val / test / holdout sets
│   ├── models/               # Model-specific feature views (General IDS, DDoS, etc.)
│   └── partitions/           # 7 simulated ISP federated partitions (IID & non-IID)
├── manifests/                # Cryptographically signed JSON manifests
├── reports/                  # Data quality, parity, and partition statistical reports
└── synthetic-fixtures/       # Committed small fixtures for automated zero-cost CI testing
```

---

## 4. Controlled Acquisition & Disk Budget Safety

Because full academic datasets can reach ~12 GiB uncompressed:
1. **Preflight Resource Checks:** `ControlledDatasetAcquisition` verifies free disk space (>10 GB threshold) and checks network download budgets (default 1 GiB limit).
2. **Explicit User Execution:** Automated pipelines and CI runners never trigger background gigabyte downloads; they run against `data/synthetic-fixtures/sample_netflow_v2.parquet` (1,400 rows, 100% feature coverage).
3. **Full Dataset Ingestion Command:**
   ```bash
   python tools/fcs_data.py download --dataset-id NF-UQ-NIDS-v2 --output-dir data/raw
   ```
