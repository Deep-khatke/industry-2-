# FCS-UDIP Seven Simulated ISP Federated Partition Report
**Partition Regime:** `STRONG_NON_IID` (Dirichlet Alpha: 0.1)
**Parent Dataset Digest:** `462c39f8e9bbf461...`
**Total Allocated Training Records:** 998
**Random Seed:** 42

---

## 1. Client Allocation Summary
| Logical Client ID | Phase 1 Mapped Tenant | Record Count | Share | Dominant Class Profiles |
|---|---|---|---|---|
| `isp_01` | `tenant-isp-alpha` | 82 | 8.2% | Benign: 61, DoS: 9, Reconnaissance: 8 |
| `isp_02` | `tenant-isp-beta` | 157 | 15.7% | Exploits: 87, Botnet: 35, Injection: 35 |
| `isp_03` | `tenant-isp-gamma` | 76 | 7.6% | DDoS: 43, Reconnaissance: 33 |
| `isp_04` | `tenant-isp-delta` | 33 | 3.3% | DoS: 17, Botnet: 9, Exploits: 4 |
| `isp_05` | `tenant-isp-epsilon` | 162 | 16.2% | Brute Force: 92, DoS: 65, Benign: 5 |
| `isp_06` | `tenant-isp-zeta` | 258 | 25.9% | Scanning: 108, Reconnaissance: 76, Benign: 39 |
| `isp_07` | `tenant-isp-eta` | 230 | 23.0% | Injection: 73, Botnet: 65, DDoS: 49 |


---

## 2. Federated Boundary Guarantees
1. **Mutual Exclusivity:** Every assigned training sample belongs to exactly one simulated ISP client (0 record duplication across clients).
2. **Train Set Isolation:** Test and validation splits are completely excluded from client federated partitions.
3. **Independent Source Holdout:** Zero samples from held-out source datasets are present in client training views.
4. **Tenant ID Parity:** Client IDs (`isp_01` .. `isp_07`) map directly to Phase 1 authorized rural ISP tenants (`tenant-isp-alpha` .. `tenant-isp-eta`).
