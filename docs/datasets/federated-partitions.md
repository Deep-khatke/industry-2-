# Federated Cyber Shield — Seven Simulated ISP Partitions

**Architecture Baseline:** FCS v1.2  
**Component:** FCS-UDIP Federated Partitioner  
**Specification Version:** 1.2.0  

---

## 1. Simulated ISP Client Identities

Federated Cyber Shield targets distributed threat detection across multiple independent rural Internet Service Providers (ISPs). To simulate this architecture without incurring multi-tenant cloud costs or requiring real customer telemetry, FCS-UDIP models **seven independent logical ISP clients**:

| Client ID | Display Name | Phase 1 Tenant ID Mapping | Simulated Infrastructure Profile |
| :--- | :--- | :--- | :--- |
| `isp_01` | Highland Rural Telecom | `tenant-isp-alpha` | Rural fiber-to-the-home (FTTH), high residential streaming |
| `isp_02` | Prairie Broadband Co-op | `tenant-isp-beta` | Fixed wireless access (FWA), agricultural IoT sensors |
| `isp_03` | Mountain Valley Net | `tenant-isp-gamma` | Regional municipal enterprise network and VoIP |
| `isp_04` | Coastal Reach ISP | `tenant-isp-delta` | Coastal maritime and port telemetry, high UDP video |
| `isp_05` | Timberland Connect | `tenant-isp-epsilon` | Rural industrial telemetry and distributed SCADA nodes |
| `isp_06` | Sunbelt Wireless | `tenant-isp-zeta` | Solar farm monitoring and distributed edge gateways |
| `isp_07` | Northwoods Fiber | `tenant-isp-eta` | Small business colocation and municipal government |

---

## 2. Partitioning Regimes

Network traffic across independent ISPs is rarely uniformly distributed (IID). FCS-UDIP implements three distinct partition regimes to benchmark federated learning convergence in Phase 3:

### 2.1 Regime A: Independent and Identically Distributed (IID)
- **Method:** Stratified allocation across classes and sources.
- **Characteristics:** Every ISP client receives an approximately equal volume of records and an identical proportion of benign and attack categories.
- **Use Case:** Establishes the theoretical upper bound for federated model convergence (FedAvg baseline).

### 2.2 Regime B: Moderately Non-IID
- **Method:** Class-conditional Dirichlet distribution with concentration parameter $\alpha = 0.5$.
- **Characteristics:** Clients exhibit moderate heterogeneity. For example, `isp_02` (agricultural IoT) exhibits higher scanning and botnet traffic, while `isp_01` has primarily benign residential flows.
- **Minimum Client Safeguard:** Enforces minimum 50 records per client to prevent empty-partition dropouts.

### 2.3 Regime C: Strongly Non-IID
- **Method:** Skewed Dirichlet allocation with concentration parameter $\alpha = 0.1$.
- **Characteristics:** Extreme statistical heterogeneity. Individual clients may only observe 1 or 2 specific attack classes (e.g., `isp_05` receives 90% of all DoS attacks, while `isp_03` receives all Brute Force attacks).
- **Use Case:** Stress-tests personalized federated learning algorithms, local gradient drift, and robust aggregation schemes.

---

## 3. Strict Boundary Rules

1. **Unique Record Assignment:** Every training record belongs to exactly one simulated ISP client. Records are never duplicated across clients.
2. **Untouched Test Sets:** Test partitions and held-out sources are never partitioned into ISP training clients. They remain completely centralized and untouched for global validation.
3. **Identical Feature Schema:** Every client parquet table adheres to the exact same canonical feature schema, enabling federated parameter averaging without dimension mismatch.
4. **Partition Manifest:** Every partitioning run produces a signed `partition_manifest.json` recording client record counts, class proportions, and cryptographic record digests.

---

## 4. Execution Commands

```bash
# Generate IID partitions
python tools/fcs_data.py partition data/processed/splits/train.parquet --regime IID --clients 7 --output-dir data/processed/partitions/iid

# Generate Moderately Non-IID partitions
python tools/fcs_data.py partition data/processed/splits/train.parquet --regime MODERATE_NON_IID --clients 7 --output-dir data/processed/partitions/moderate_non_iid

# Generate Strongly Non-IID partitions
python tools/fcs_data.py partition data/processed/splits/train.parquet --regime STRONG_NON_IID --clients 7 --output-dir data/processed/partitions/strong_non_iid
```
