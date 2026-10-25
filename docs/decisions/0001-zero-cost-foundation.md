# Architecture Decision Record (ADR) 0001: Zero-Cost Foundation and Deferred Cloud Provisioning

## Status
Accepted

## Context
Federated Cyber Shield (FCS) v1.2 is a privacy-preserving cybersecurity platform designed for rural Internet Service Providers (ISPs). Phase 1 establishes the engineering foundation, telemetry ingestion interfaces, multi-tenant security primitives, and data contracts.

The execution budget for Phase 1 is **₹0 / $0**. The platform must be strictly cloud-first and cloud-deployable without incurring charges, provisioning pay-as-you-go infrastructure, or activating credit-card-backed cloud trials.

## Decision
1. **Three-Tier Execution Level Strategy**:
   - **Level A (Workspace Verification)**: All development, testing, linting, type-checking, and synthetic traffic generation run locally using free open-source tools (Python 3.11+, pytest, Ruff, Mypy, Pydantic, OpenTofu, SQLite).
   - **Level B (Free Hosted CI)**: Ephemeral testing runs via GitHub Actions standard hosted runners using pinned actions and minimal permissions, strictly within free tier quotas.
   - **Level C (Production Readiness)**: Cloud infrastructure is defined completely using OpenTofu IaC modules. The modules are verified statically (`tofu fmt`, `tofu validate`, static policy inspection), but actual deployment to AWS is designated `BLOCKED_BY_ZERO_COST_POLICY` until future funding authorization.

2. **No Cloud Resources Provisioned**:
   - AWS EC2, NLB, Kinesis, KMS, and S3 are modeled in OpenTofu configuration files but never applied (`tofu apply` is prohibited).
   - Offline validation runs with `skip_credentials_validation = true` and `skip_metadata_api_check = true`.

3. **Pluggable Ingestion Streaming**:
   - The streaming pipeline uses an abstract `StreamSink` protocol.
   - Development and testing execute against `MemoryStreamSink` (ephemeral) and `SQLiteStreamSink` (durable zero-cost persistence with WAL mode).
   - `KinesisStreamSink` is provided for future AWS integration but is disabled by default and requires no AWS credentials.

## Consequences
- **Positive**: 100% compliance with the zero-cost mandate; zero billable infrastructure charges; complete offline testability.
- **Trade-offs**: Real cross-account AWS IAM trust boundaries and live physical network NLB failover cannot be verified until Phase 2 or when paid cloud environments are explicitly funded.
