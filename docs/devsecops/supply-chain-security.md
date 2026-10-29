# Federated Cyber Shield (FCS) v1.2 — Software Supply Chain Security

## 1. Supply Chain Architecture & Integrity Model

FCS implements supply chain security controls adhering to the SLSA (Supply-chain Levels for Software Artifacts) framework and NIST SP 800-218 (Secure Software Development Framework).

```mermaid
flowchart LR
    SourceCode[Git Source Repository] --> DepPinning[Explicit Version Pinning & Hashes]
    DepPinning --> HermeticBuild[Hermetic Multi-Stage Build]
    HermeticBuild --> SBOMGen[SBOM Generator (CycloneDX + SPDX)]
    HermeticBuild --> ArtifactHash[SHA-384 Artifact Digestion]
    ArtifactHash --> DualSign[Dual Signature Engine (ECDSA + ML-DSA-65)]
    DualSign --> VerifiedRelease[Immutable Release Candidate]
```

---

## 2. Dependency Pinning & Audit Controls

1. **Python Dependencies**:
   - Specified across workspace packages (`packages/contracts`, `services/api`, etc.) and `pyproject.toml`.
   - Core runtime packages are audited by `tools/security/dependency_audit.py` to prevent known CVEs and malicious typosquatting.
2. **Node.js Dependencies**:
   - Pinned strictly in `apps/security-dashboard/package-lock.json`.
   - Built exclusively using `npm ci` to guarantee byte-for-byte reproducibility across local and CI runner environments.
3. **Container Base Images**:
   - Production Dockerfiles pin official, minimal Debian/Alpine Linux base images with non-root security contexts (`appuser:appgroup`).

---

## 3. Cryptographic Tamper Evident Verification

All 69 release artifacts (models, configuration templates, database schemas, and documentation runbooks) are indexed in `artifacts/phase11/release-manifests/phase11_release_manifest.json` with their SHA-384 cryptographic hashes and verified before distribution.
