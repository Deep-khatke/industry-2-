# FCS-UDIP Seven Simulated ISP Federated Partition Report
**Partition Regime:** `IID` (Uniform Stratified)
**Parent Dataset Digest:** `462c39f8e9bbf461...`
**Total Allocated Training Records:** 998
**Random Seed:** 42

---

## 1. Client Allocation Summary
| Logical Client ID | Phase 1 Mapped Tenant | Record Count | Share | Dominant Class Profiles |
|---|---|---|---|---|
| `isp_01` | `tenant-isp-alpha` | 147 | 14.7% | Brute Force: 17, Scanning: 17, Reconnaissance: 17 |
| `isp_02` | `tenant-isp-beta` | 145 | 14.5% | Reconnaissance: 17, Botnet: 17, Scanning: 17 |
| `isp_03` | `tenant-isp-gamma` | 143 | 14.3% | Reconnaissance: 17, Botnet: 17, Exploits: 16 |
| `isp_04` | `tenant-isp-delta` | 142 | 14.2% | Reconnaissance: 17, Injection: 16, Exploits: 16 |
| `isp_05` | `tenant-isp-epsilon` | 141 | 14.1% | Reconnaissance: 17, Botnet: 16, Scanning: 16 |
| `isp_06` | `tenant-isp-zeta` | 141 | 14.1% | Reconnaissance: 17, Brute Force: 16, Scanning: 16 |
| `isp_07` | `tenant-isp-eta` | 139 | 13.9% | Injection: 16, Scanning: 16, Botnet: 16 |


---

## 2. Federated Boundary Guarantees
1. **Mutual Exclusivity:** Every assigned training sample belongs to exactly one simulated ISP client (0 record duplication across clients).
2. **Train Set Isolation:** Test and validation splits are completely excluded from client federated partitions.
3. **Independent Source Holdout:** Zero samples from held-out source datasets are present in client training views.
4. **Tenant ID Parity:** Client IDs (`isp_01` .. `isp_07`) map directly to Phase 1 authorized rural ISP tenants (`tenant-isp-alpha` .. `tenant-isp-eta`).
