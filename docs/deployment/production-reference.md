# Federated Cyber Shield (FCS) v1.2 — Production-Reference Deployment Guide

## 1. Reference Architecture & Security Hardening

The `PRODUCTION_REFERENCE` deployment is designed for sovereign telecommunications carrier deployments on bare-metal Linux servers or containerized orchestrators without commercial cloud dependencies.

### Hardening Features:
- Non-root user execution (`UID 10001:10001`).
- Read-only root filesystem with writable `/data` mount for SQLite WAL.
- Hardened HTTP security headers (`Content-Security-Policy`, `HSTS`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`).
- Sliding-window rate limiting on authentication endpoints.
- Auto-response locked down (`Gate G13: BLOCKED`).

---

## 2. Launching via Docker Compose

```bash
cd infrastructure/containers/production-reference

# 1. Create secure environment file
cat <<EOF > .env
FCS_ENV=PRODUCTION_REFERENCE
FCS_SECRET_KEY=$(openssl rand -hex 32)
FCS_DATABASE_URL=sqlite:////data/fcs_production.db
FCS_AUTO_RESPONSE_ENABLED=false
FCS_ENFORCE_ZERO_COST=true
FCS_ALLOW_DEMO_ENDPOINTS=false
EOF

# 2. Start container stack
docker compose -f docker-compose.prod-reference.yml up -d
```

---

## 3. Post-Deployment Verification

Check container logs and health endpoint:
```bash
curl -s http://localhost:8000/health | jq .
```
Expected output:
```json
{
  "status": "healthy",
  "version": "1.2.0",
  "environment": "PRODUCTION_REFERENCE",
  "auto_live_gated": true
}
```
