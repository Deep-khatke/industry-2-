# Federated Cyber Shield (FCS) v1.2 — Integration Environment Guide

## 1. Integration Profile Overview

The `INTEGRATION` profile validates the entire end-to-end dataflow between telemetry exporters, stream windowing, multi-stage detection, and incident dispatching under automated testing conditions.

---

## 2. Running Automated Integration Tests

```bash
# Set environment
export FCS_ENV="INTEGRATION"
export FCS_AUTO_RESPONSE_ENABLED="false"
export FCS_ALLOW_DEMO_ENDPOINTS="false"

# Run integration test suite
python -m pytest tests/phase4-integration/ tests/system/end_to_end/ tests/phase11/release/ -v
```

---

## 3. Containerized Integration Testing

For hermetic validation inside Linux containers:

```bash
docker compose -f infrastructure/containers/integration/docker-compose.integration.yml up --abort-on-container-exit --exit-code-from integration-tests
```
