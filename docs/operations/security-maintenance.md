# Federated Cyber Shield (FCS) v1.2 — Security Maintenance Runbook

## 1. Routine Maintenance Schedule

| Maintenance Task | Recommended Frequency | Responsible Team | Verification Command / Procedure |
|---|---|---|---|
| **Zero-Cost Static Scan** | Weekly / Prior to Commits | DevSecOps Lead | `python tools/zero-cost-audit/scanner.py` |
| **Dependency Vulnerability Audit** | Bi-weekly | Security Engineer | `python tools/security/dependency_audit.py` |
| **Atomic Database Backup** | Daily | SRE / Database Admin | `BackupManager.create_backup()` |
| **Disaster Recovery Sandboxed Test** | Monthly | SRE Lead | `RestoreValidator.validate_restore()` |
| **JWT Secret Rotation** | Quarterly | Platform Admin | Update `FCS_SECRET_KEY` in environment |
| **Dual Cryptographic Manifest Audit** | Per Release | Cryptography Lead | `python tools/release/build_release_manifest.py` |

---

## 2. JWT Credential Invalidation & Token Revocation

When an analyst departs or credentials are compromised:
1. Invalidate user tokens via `POST /v1/auth/logout` with Bearer token.
2. In emergency scenarios, rotate `FCS_SECRET_KEY` in the environment configuration to instantly invalidate all outstanding active JWT sessions across the cluster.
