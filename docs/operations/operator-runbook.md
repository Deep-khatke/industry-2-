# Federated Cyber Shield (FCS) v1.2 — Operator Runbook

## 1. Quickstart & Service Launch

### 1.1 Local Development Startup
```bash
# 1. Install workspace dependencies
python -m pip install -e . --no-deps

# 2. Launch FastAPI API server (Port 8000)
uvicorn services.api.src.fcs_api.app:app --host 0.0.0.0 --port 8000 --reload

# 3. Launch Security Dashboard (Port 5173)
cd apps/security-dashboard
npm run dev
```

### 1.2 Production Reference (Containerized)
```bash
cd infrastructure/containers/production-reference
docker compose -f docker-compose.prod-reference.yml up -d
```

---

## 2. Health & Observability Monitoring

- **API Health Check**: `GET /health` returns `{ "status": "healthy", "version": "1.2.0", "environment": "PRODUCTION_REFERENCE", "auto_live_gated": true }`.
- **Prometheus Metrics**: `GET /metrics` exports:
  - `fcs_api_requests_total{endpoint, status_code}`
  - `fcs_hmd_inference_seconds_count`
  - `fcs_incidents_active_count{tenant_id}`
  - `fcs_flow_ingestion_rate_per_sec`
- **Dashboard Access**: Open browser at `http://localhost:8000/` or `http://localhost:5173/`.

---

## 3. Incident Investigation Workflow

1. Log into Dashboard using tenant credentials.
2. Navigate to **Incidents** view.
3. Review anomalous flow features (packet rate, byte ratio, port distribution).
4. If action recommended, review proposed rule:
   - Verify target IP is NOT a protected resource.
   - Verify duration TTL is within policy bounds (e.g. 3600s).
5. As `SECURITY_ADMIN`, click **Approve Action** to simulate mitigation in Firewall Simulator.
