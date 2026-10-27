# Phase 6 Handoff — Flower Federated Learning Architecture & Integration

**From:** FCS Phase 5 Hierarchical Detection Architecture Team  
**To:** FCS Phase 6 Federated Learning Architecture Team  
**Architecture Baseline:** Federated Cyber Shield v1.2  
**Component:** Flower Federated Client & SuperLink Aggregation  
**Budget:** Strictly ₹0.00 / $0.00 (Zero-Cost Local CPU Execution)  
**Status:** READY FOR PHASE 6 COMMENCEMENT  

---

## 1. Context and Mission for Phase 6

Phase 5 has established the FCS-HMD Hierarchical Multi-Model Intrusion Detection Engine, incorporating Level 1 general detection, tenant anomaly baselines, conditionally routed attack specialists, and deterministic evidence fusion.

Phase 6 will introduce **Flower-based Federated Learning** across rural Internet Service Providers. Rather than centralizing sensitive raw subscriber NetFlow records in the cloud, each simulated ISP will train local model updates on its own partition and send only model parameter weights to the Flower SuperLink aggregation server.

> [!IMPORTANT]
> Flower-based federated learning has **not** been implemented in Phase 5. Phase 5 prepares the neural architectures, fixed schemas, training hooks, and partition mappings required for Phase 6 execution.

---

## 2. Decoupled Neural Architecture for Federated Averaging (FedAvg)

Phase 3 and Phase 5 have standardized the neural network `TabularMLPNet` in `services/ml_training/src/fcs_ml/models/mlp.py` specifically for compatibility with Flower `NumPyClient`:

```python
from fcs_ml.models.mlp import TabularMLPNet

# Reconstruct identical architecture across all Flower SuperNodes
net = TabularMLPNet(
    input_dim=14,          # Fixed Deployable Track Schema (deployable_v1)
    hidden_dims=[128, 64], # Standard conservative tabular layers
    output_dim=1,          # Binary threat detection (sigmoid probability output)
    dropout_rate=0.2,
    use_batch_norm=True,
)
```

### Deterministic Parameter Ordering
`TabularMLPNet` guarantees:
1. **Fixed layer sequence:** `fc1` -> `bn1` -> `relu` -> `dropout` -> `fc2` -> `bn2` -> `relu` -> `out`.
2. **Deterministic weight serialization:**
   ```python
   # Convert PyTorch state dict to Flower NumPy ndarrays:
   weights = [val.cpu().numpy() for _, val in net.state_dict().items()]
   ```
3. **Weight restoration after global FedAvg aggregation:**
   ```python
   params_dict = zip(net.state_dict().keys(), weights)
   state_dict = {k: torch.tensor(v) for k, v in params_dict}
   net.load_state_dict(state_dict, strict=True)
   ```

---

## 3. Fixed Feature Schema (deployable_v1)

Phase 6 Flower clients must strictly adhere to the 14-feature deployable schema locked in Phase 2 and validated in Phase 4/5:

```json
[
  "L4_SRC_PORT",
  "L4_DST_PORT",
  "PROTOCOL",
  "IN_BYTES",
  "IN_PKTS",
  "OUT_BYTES",
  "OUT_PKTS",
  "FLOW_DURATION_MILLISECONDS",
  "TCP_FLAGS",
  "CLIENT_TCP_FLAGS",
  "SERVER_TCP_FLAGS",
  "DURATION_IN",
  "DURATION_OUT",
  "MIN_TTL"
]
```
Schema Hash: `92f73ab100db06d82b252e0c86fac983083232fb247baf1cdf57afd6ba8dcbf0`

---

## 4. Seven Simulated ISP Partitions (Phase 2 Lineage)

Phase 2 generated, validated, and signed seven non-overlapping ISP federated partitions in `data/processed/partitions/`:

| Partition ID | Client Role | Split Policy | Manifest Path | Sample Count |
|---|---|---|---|---|
| `isp_partition_1` | Tier 1 Rural Backbone ISP | Non-IID Dirichlet ($\alpha=0.5$) | `data/processed/partitions/isp_partition_1.json` | 147 |
| `isp_partition_2` | Regional Wireless ISP | Non-IID Dirichlet ($\alpha=0.5$) | `data/processed/partitions/isp_partition_2.json` | 145 |
| `isp_partition_3` | Municipal Fiber ISP | Non-IID Dirichlet ($\alpha=0.5$) | `data/processed/partitions/isp_partition_3.json` | 143 |
| `isp_partition_4` | Community Cooperative ISP | Non-IID Dirichlet ($\alpha=0.5$) | `data/processed/partitions/isp_partition_4.json` | 142 |
| `isp_partition_5` | Enterprise Transit Provider | Non-IID Dirichlet ($\alpha=0.5$) | `data/processed/partitions/isp_partition_5.json` | 141 |
| `isp_partition_6` | Academic Campus Network | Non-IID Dirichlet ($\alpha=0.5$) | `data/processed/partitions/isp_partition_6.json` | 141 |
| `isp_partition_7` | Rural Agricultural Co-op | Non-IID Dirichlet ($\alpha=0.5$) | `data/processed/partitions/isp_partition_7.json` | 139 |

Phase 6 Flower clients can directly bind to their assigned partition file in `data/processed/partitions/` without reshuffling or re-partitioning.

---

## 5. Reusable Local Training & Evaluation Template

Phase 6 can implement the `flwr.client.NumPyClient` interface using existing building blocks:

```python
import flwr as fl
import torch
from fcs_ml.data.dataset import create_dataloader
from fcs_ml.models.mlp import TabularMLPNet

class FCSFlowerClient(fl.client.NumPyClient):
    def __init__(self, client_id: str, train_loader, val_loader):
        self.client_id = client_id
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.net = TabularMLPNet(input_dim=14, hidden_dims=[128, 64], output_dim=1)
        self.optimizer = torch.optim.AdamW(self.net.parameters(), lr=1e-3, weight_decay=1e-4)
        self.criterion = torch.nn.BCEWithLogitsLoss()

    def get_parameters(self, config):
        return [val.cpu().numpy() for _, val in self.net.state_dict().items()]

    def set_parameters(self, parameters):
        params_dict = zip(self.net.state_dict().keys(), parameters)
        state_dict = {k: torch.tensor(v) for k, v in params_dict}
        self.net.load_state_dict(state_dict, strict=True)

    def fit(self, parameters, config):
        self.set_parameters(parameters)
        self.net.train()
        for batch_x, batch_y in self.train_loader:
            self.optimizer.zero_grad()
            out = self.net(batch_x)
            loss = self.criterion(out.squeeze(-1), batch_y.float())
            loss.backward()
            self.optimizer.step()
        return self.get_parameters(config={}), len(self.train_loader.dataset), {}

    def evaluate(self, parameters, config):
        self.set_parameters(parameters)
        self.net.eval()
        loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for batch_x, batch_y in self.val_loader:
                out = self.net(batch_x).squeeze(-1)
                loss += self.criterion(out, batch_y.float()).item()
                preds = (torch.sigmoid(out) >= 0.5).long()
                correct += (preds == batch_y).sum().item()
                total += batch_y.size(0)
        return float(loss / len(self.val_loader)), total, {"accuracy": float(correct / total)}
```

---

## 6. Model Artifact Integrity & Registry Lineage

All Phase 5 candidate models are registered in `artifacts/candidate-models/` with SHA-256 digests:

| Model ID | Architecture | Digest | Status in Phase 6 |
|---|---|---|---|
| `lightgbm_deployable_subset` | LightGBM Booster | `f776a93db005a242c329d183a04f83899aaaaf72972ed884525bacda368a8f58` | Baseline General Detector |
| `pytorchmlp_research_benchmark` | PyTorch MLP | `e68224749323f46f3a38a7c85885c490a6e60b13ae42c744f128bc4e8e52dbb1` | Primary Seed for Federated Training |
| `isolationforest_anomaly_tenant` | Isolation Forest | `93efc8df38b5b2e942d4762c9ac99cf02752cd9edeb7fe709c356e98d9ca1b8f` | **Tenant-Local Only (Do NOT Federate)** |
| `autoencoder_anomaly` | PyTorch Autoencoder | `bd83528f6448115e603354f1679aa9c7b334a07bd9a8b5f512c81328c63766a4` | **Tenant-Local Only (Do NOT Federate)** |
| `lightgbm_ddos_specialist` | LightGBM Specialist | `a43bbb2c9930e43b9375901ad1a9c033f2b14c5168a06447f7ee2a6eb16fc0dd` | Auxiliary Deployment Specialist |
| `lightgbm_scanning_specialist` | LightGBM Specialist | `db34b856925c81762b348786ab0834e03d7b3a67385cd0d9850b5843d83c656f` | Auxiliary Deployment Specialist |

---

## 7. Non-Federated Architectural Boundary

> [!CAUTION]
> **Tenant-Specific Anomaly Models Must Remain Strictly Outside Federated Learning:**
> - The `IsolationForestAnomalyModel` and `AutoencoderAnomalyModel` capture ISP-specific benign traffic distributions.
> - **Do NOT** aggregate anomaly model parameters across tenants. Sharing or averaging anomaly models across tenants will cause cross-tenant privacy leakage and degrade per-ISP benign baselines.
> - Federated learning in Phase 6 must focus exclusively on the **shared General Threat Detector** (`TabularMLPNet`).

---

## 8. Model Replacement and Rollback Interface

When Phase 6 produces an aggregated global model that outperforms the baseline general detector, it can be promoted into the active `DetectionBundle` via the Phase 5 engine API:

```python
from fcs_ml.hmd.bundle import DetectionBundle
from fcs_ml.hmd.executor import HierarchicalDetectionEngine

engine = HierarchicalDetectionEngine()

# Construct updated bundle incorporating federated model
updated_bundle = DetectionBundle(
    bundle_id="fcs-hmd-bundle-v2-federated",
    version="1.3.0",
    general_model_id="federated_tabular_mlp_v1",
    anomaly_model_id="isolationforest_anomaly_tenant",
    specialist_model_ids=["lightgbm_ddos_specialist", "lightgbm_scanning_specialist"],
    authorized_by="security_admin",
    status="ACTIVE",
).seal()

# Authorized activation
result = engine.activate_bundle(updated_bundle, authorized_by="security_admin", role="PLATFORM_ADMIN")

# If degradation is detected, immediate atomic rollback is supported:
# engine.rollback_bundle(authorized_by="security_admin", role="PLATFORM_ADMIN")
```

---

## 9. Phase 6 Checklist for Architecture Team

- [ ] Install `flwr>=1.7.0` in the local Python environment (strictly zero-cost).
- [ ] Implement `FCSFlowerClient` wrapping `TabularMLPNet`.
- [ ] Connect clients to the 7 pre-existing ISP partitions in `data/processed/partitions/`.
- [ ] Implement Flower Server with `FedAvg` and differential privacy / secure aggregation hooks.
- [ ] Evaluate global federated model convergence across rounds.
- [ ] Verify that tenant anomaly models remain isolated locally on each client node.
- [ ] Register new global model in `CandidateModelRegistry` and activate via `DetectionBundle`.
