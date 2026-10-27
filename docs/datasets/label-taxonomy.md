# Federated Cyber Shield — Attack Label Taxonomy & Normalization

**Architecture Baseline:** FCS v1.2  
**Component:** FCS-UDIP Label Normalizer & Target Taxonomy  
**Specification Version:** 1.2.0  

---

## 1. Unified Attack Taxonomy

Heterogeneous intrusion detection benchmarks use conflicting, non-standardized attack nomenclature (e.g., `DDoS attacks-LOIC-HTTP`, `DDoS-HOIC`, `ddos`, `DoS attacks-GoldenEye`, `password`, `FTP-BruteForce`, `xss`). FCS-UDIP normalizes all raw labels into a standardized **14-class canonical taxonomy**:

1. `Benign` — Normal legitimate network baseline traffic.
2. `DDoS` — Distributed Denial of Service floods across transport/application layers (e.g., LOIC, HOIC, UDP/TCP reflection floods).
3. `DoS` — Single-source Denial of Service attacks (e.g., Slowloris, Hulk, GoldenEye, Slowhttptest).
4. `Reconnaissance` — Active host discovery, probe packets, and perimeter enumeration.
5. `Scanning` — Service and port scanning, OS fingerprinting (e.g., Nmap SYN scans, OS_Fingerprint, Service_Scan).
6. `Botnet` — Command-and-control communication and coordinated malware fleet telemetry.
7. `Brute Force` — Authentication credential stuffing and dictionary attacks against SSH, FTP, RDP, or HTTP login endpoints.
8. `Injection` — Code and query injection vulnerabilities (e.g., SQL Injection, OS Command Injection, XML/LDAP injection).
9. `Exploits` — Vulnerability exploitation payloads (e.g., Heartbleed, EternalBlue, zero-day CVE execution).
10. `Fuzzers` — Algorithmic protocol fuzzing and malformed packet generation.
11. `Backdoor` — Unauthorized persistence mechanisms and covert channel communication.
12. `Web Attack` — Cross-Site Scripting (XSS), directory traversal, brute-force form attacks.
13. `Infiltration` — Lateral movement and post-compromise privilege escalation.
14. `Unknown` — Unmapped, ambiguous, or unsupported attack strings.

---

## 2. Cross-Dataset Normalization Mapping Matrix

FCS-UDIP resolves raw strings based on the originating dataset source:

### 2.1 NF-CSE-CIC-IDS2018-v2
| Raw String in Dataset | Canonical Taxonomy Class | Binary Label |
| :--- | :--- | :--- |
| `Benign` | `Benign` | 0 |
| `DDoS attacks-LOIC-HTTP` | `DDoS` | 1 |
| `DDOS attack-HOIC` | `DDoS` | 1 |
| `DDOS attack-LOIC-UDP` | `DDoS` | 1 |
| `DoS attacks-Slowloris` | `DoS` | 1 |
| `DoS attacks-Hulk` | `DoS` | 1 |
| `DoS attacks-GoldenEye` | `DoS` | 1 |
| `DoS attacks-SlowHTTPTest` | `DoS` | 1 |
| `FTP-BruteForce` | `Brute Force` | 1 |
| `SSH-Bruteforce` | `Brute Force` | 1 |
| `SQL Injection` | `Injection` | 1 |
| `Brute Force -Web` | `Brute Force` | 1 |
| `Brute Force -XSS` | `Web Attack` | 1 |
| `Infilteration` | `Infiltration` | 1 |
| `Bot` | `Botnet` | 1 |

### 2.2 NF-BoT-IoT-v2
| Raw String in Dataset | Canonical Taxonomy Class | Binary Label |
| :--- | :--- | :--- |
| `Benign` | `Benign` | 0 |
| `DDoS` | `DDoS` | 1 |
| `DoS` | `DoS` | 1 |
| `Reconnaissance` | `Reconnaissance` | 1 |
| `OS_Fingerprint` | `Scanning` | 1 |
| `Service_Scan` | `Scanning` | 1 |
| `Keylogging` | `Exploits` | 1 |
| `Data_Exfiltration` | `Exploits` | 1 |

### 2.3 NF-ToN-IoT-v2
| Raw String in Dataset | Canonical Taxonomy Class | Binary Label |
| :--- | :--- | :--- |
| `normal` / `Benign` | `Benign` | 0 |
| `backdoor` | `Backdoor` | 1 |
| `ddos` | `DDoS` | 1 |
| `dos` | `DoS` | 1 |
| `injection` | `Injection` | 1 |
| `password` | `Brute Force` | 1 |
| `ransomware` | `Exploits` | 1 |
| `scanning` | `Scanning` | 1 |
| `xss` | `Injection` | 1 |

---

## 3. Strict Target Leakage Prevention

The pipeline introduces the `TargetLeakageError` exception to prevent ML models from cheating via shortcut learning:

### Prohibited Predictor Columns
The following columns are strictly forbidden from entering any training or evaluation feature matrix $X$:
- `Attack`, `attack`, `original_attack_label`
- `Label`, `label`, `binary_label`
- `canonical_attack_label`
- `dataset_source` (prevents model from exploiting testbed artifacts as predictors)
- `label_mapping_version`
- `split_id`
- `isp_client_id` (prevents client shortcut correlation in federated learning)
- `tenant_id`
- `event_id`

`LabelNormalizer.validate_predictor_features()` inspects all candidate feature column names and raises `TargetLeakageError` immediately if any target, metadata, or provenance column is detected.
