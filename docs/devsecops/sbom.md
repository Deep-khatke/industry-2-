# Federated Cyber Shield (FCS) v1.2 — Software Bill of Materials (SBOM)

## 1. SBOM Standards Compliance

FCS provides machine-readable Software Bill of Materials (SBOM) in two industry-standard formats, satisfying NTIA Minimum Elements for Software Bill of Materials and Executive Order 14028:

1. **CycloneDX v1.5 JSON**: Located at `artifacts/phase11/sbom/cyclonedx_sbom.json`.
2. **SPDX v2.3 JSON**: Located at `artifacts/phase11/sbom/spdx_sbom.json`.

---

## 2. Component Inventory Summary

The SBOM generator (`tools/sbom/generate_sbom.py`) catalogs 25 core software components spanning backend frameworks, machine learning runtimes, cryptographic libraries, and frontend dependencies:

| Component Name | Version | Ecosystem | Purpose | License |
|---|---|---|---|---|
| `fastapi` | 0.110.0 | PyPI | REST API Engine | MIT |
| `uvicorn` | 0.28.0 | PyPI | ASGI Web Server | BSD-3-Clause |
| `pydantic` | 2.6.4 | PyPI | Schema Data Validation | MIT |
| `pyjwt` | 2.8.0 | PyPI | JWT Authentication | MIT |
| `cryptography` | 42.0.5 | PyPI | Cryptographic Primitives | Apache-2.0 / BSD |
| `lightgbm` | 4.3.0 | PyPI | Gradient Boosting Decision Trees | MIT |
| `scikit-learn` | 1.4.1 | PyPI | Preprocessing & Isolation Forest | BSD-3-Clause |
| `opacus` | 1.4.0 | PyPI | Differential Privacy Engine | Apache-2.0 |
| `flower` (`flwr`) | 1.7.0 | PyPI | Federated Learning Orchestration | Apache-2.0 |
| `numpy` | 1.26.4 | PyPI | Mathematical Vector Math | BSD-3-Clause |
| `pandas` | 2.2.1 | PyPI | Tabular Data Processing | BSD-3-Clause |
| `rfc8785` | 0.1.4 | PyPI | Canonical JSON Formatting | Apache-2.0 |
| `pytest` | 9.1.1 | PyPI | Test Execution & Verification | MIT |
| `react` | 18.3.1 | npm | User Interface View Engine | MIT |
| `react-dom` | 18.3.1 | npm | DOM Renderer | MIT |
| `lucide-react` | 0.474.0 | npm | Security UI Iconography | ISC |
| `vite` | 5.4.21 | npm | Frontend Bundler | MIT |
| `tailwindcss` | 3.4.17 | npm | Design Token Utility Styling | MIT |
| `typescript` | 5.5.3 | npm | Static Type Checking | Apache-2.0 |

---

## 3. Automation and Regenerability

SBOMs can be regenerated at any time using the standalone zero-cost tool:

```bash
python tools/sbom/generate_sbom.py
```
Outputs are automatically written to `artifacts/phase11/sbom/`.
