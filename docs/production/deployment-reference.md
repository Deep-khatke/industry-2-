# Federated Cyber Shield (FCS) v1.2 — Deployment Reference

## 1. Multi-Environment Profiles

FCS v1.2 defines four strictly partitioned runtime environment profiles:

| Environment Profile | Target Purpose | Auth & Credentials | Ingestion Mode | Response Mode | Demo Endpoints |
|---|---|---|---|---|---|
| `DEVELOPMENT` | Local workstation, unit tests, fast feedback | Mock accounts permitted | In-memory synthetic | Simulator Only | Allowed |
| `INTEGRATION` | Multi-service integration, automated CI matrix | Strict JWT validation | In-memory synthetic | Simulator Only | Disallowed |
| `STAGING_REFERENCE` | Pre-production validation, customer dry-runs | Strong secrets enforced (>= 32 chars) | Replay file / network | Simulator Only | Disallowed |
| `PRODUCTION_REFERENCE` | Sovereign ISP bare-metal/container reference | Strong secrets, hardened security headers | Native IPFIX / NetFlow v9 | Simulator Only (`AUTO_LIVE` BLOCKED) | Disallowed |

---

## 2. Docker & Container Topologies

### 2.1 Development Profile (`infrastructure/containers/development/`)
- Single-command orchestration via `docker-compose.yml`.
- Hot-reloading FastAPI backend on port `8000`.
- Vite development dashboard on port `5173`.
- In-memory mock databases and instant seed generation.

```bash
cd infrastructure/containers/development
docker compose up -d
```

### 2.2 Integration Profile (`infrastructure/containers/integration/`)
- Production-like multi-container topology (`docker-compose.integration.yml`).
- Ephemeral SQLite test instances with strict migrations.
- Complete execution of synthetic DDoS and PortScan attack replays.

```bash
docker compose -f infrastructure/containers/integration/docker-compose.integration.yml run --rm integration-tests
```

### 2.3 Production-Reference Profile (`infrastructure/containers/production-reference/`)
- Hardened multi-stage Docker builds (`Dockerfile.backend`, `Dockerfile.frontend`).
- Non-root runtime user (`appuser:appgroup` UID 10001).
- Immutable, static dashboard distribution compiled into `/app/dist` and served under strict Content Security Policies.
- Prometheus observability exposed on `/metrics`.
- Zero-cost, locally reproducible stack with persistent WAL-backed SQLite volumes.

---

## 3. Configuration Management & Environment Variables

The backend loads configuration from YAML environment files (`configs/environments/{profile}.yaml`) overridden by system environment variables:

```bash
# Critical Production Settings
export FCS_ENV="PRODUCTION_REFERENCE"
export FCS_SECRET_KEY="<cryptographically_secure_random_key_min_32_bytes>"
export FCS_DATABASE_URL="sqlite:////data/fcs_production.db"
export FCS_ENFORCE_ZERO_COST="true"
export FCS_AUTO_RESPONSE_ENABLED="false"  # Invariant: Must remain false
export FCS_ALLOW_DEMO_ENDPOINTS="false"
```
