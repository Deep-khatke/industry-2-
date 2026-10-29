# Federated Cyber Shield (FCS) v1.2 — Development Release Procedure

## 1. Release Architecture & Principles

The FCS release procedure enforces:
1. **Zero-Cost Verification**: Full validation completed locally and on free CI runners.
2. **Reproducible Digests**: SHA-384 digestion across all 69 release files.
3. **Dual Signing**: ECDSA P-256 for conventional PKI compatibility + NIST ML-DSA-65 for quantum resistance.
4. **Canonical JSON Serialization**: Adherence to RFC 8785 for consistent hash calculation across platforms.

---

## 2. Step-by-Step Release Workflow

```mermaid
flowchart TD
    Step1[1. Clean Workspace & Rebase on main] --> Step2[2. Run Zero-Cost Static Scan]
    Step2 --> Step3[3. Run Full Test Suite (360 tests)]
    Step3 --> Step4[4. Generate SBOMs (CycloneDX & SPDX)]
    Step4 --> Step5[5. Execute Performance Benchmarks]
    Step5 --> Step6[6. Build Dual-Signed Release Manifest]
    Step6 --> Step7[7. Execute Unified Gate Audit]
    Step7 --> Step8[8. Verify Gate Verdict]
```

### Detailed Commands:

```bash
# Step 1: Scan for credentials and cloud cost violations
python tools/zero-cost-audit/scanner.py

# Step 2: Run all unit, integration, and security tests
python -m pytest tests/

# Step 3: Generate machine-readable SBOMs
python tools/sbom/generate_sbom.py

# Step 4: Run performance benchmarks
python -m tools.performance.benchmark_suite

# Step 5: Generate and verify dual signatures
python tools/release/build_release_manifest.py

# Step 6: Execute unified verification script
python scripts/verify_phase11.py
```

---

## 3. Post-Release Verification

Verify the release verdict in `artifacts/phase11/reports/phase11_verification_summary.json`:
- `verdict` MUST equal `"DEVELOPMENT_RELEASE_VERIFIED"`.
- Gate `G13` MUST remain `"BLOCKED"`.
- Gates `G01` through `G12`, `G14`, and `G15` MUST equal `"PASS_DEVELOPMENT"`.
