"""FastAPI Application Entry Point for Federated Cyber Shield (Hardened Phase 11)."""

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
import logging
from pathlib import Path
import sys
import time
from typing import Any
import uuid

# Bootstrap internal services path
_project_root = Path(__file__).resolve().parents[4]
for _src in [
    _project_root / "services" / "federated-learning" / "src",
    _project_root / "services" / "governance" / "src",
    _project_root / "services" / "ml_training" / "src",
    _project_root / "services" / "pilot-management" / "src",
]:
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import get_db, init_db, seed_demo_data
from .routes.actions import router as actions_router
from .routes.auth import router as auth_router
from .routes.detection import router as detection_router
from .routes.dev import router as dev_router
from .routes.federation import dev_router as federation_dev_router
from .routes.federation import router as federation_router
from .routes.governance import router as governance_router
from .routes.incidents import router as incidents_router
from .routes.overview import router as overview_router
from .routes.pilot import dev_router as pilot_dev_router
from .routes.pilot import router as pilot_router
from .routes.response_policy import router as response_policy_router

logger = logging.getLogger("fcs_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle handler with environment safety validation."""
    logger.info(f"Initializing FCS Platform in [{settings.environment}] mode...")
    if settings.environment in ("PRODUCTION_REFERENCE", "STAGING_REFERENCE"):
        settings.validate_production_configuration()

    init_db()
    if settings.allow_demo_credentials and settings.is_development:
        logger.info("Seeding development demo accounts and baseline configurations...")
        seed_demo_data()

    logger.info(f"FCS Platform initialized successfully. Response mode: {settings.response_mode}")
    yield
    logger.info("FCS Platform shutting down.")


app = FastAPI(
    title="Federated Cyber Shield (FCS) API",
    version="1.2.0",
    description="Real-time threat detection, security dashboard backend, and manual response policy engine.",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# CORS Configuration (Restricted in non-development)
cors_origins = ["*"] if settings.is_development else settings.cors_allowed_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Security Headers & Request Correlation Middleware
@app.middleware("http")
async def security_and_tracing_middleware(request: Request, call_next: Callable[[Request], Any]) -> Response:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    t0 = time.time()

    response: Response = await call_next(request)

    duration = time.time() - t0
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "connect-src 'self' http://127.0.0.1:* http://localhost:* ws://127.0.0.1:* ws://localhost:*"
    )
    if not settings.is_development:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # Log operational API activity
    if request.url.path not in ("/healthz", "/metrics"):
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} -> {response.status_code} ({duration * 1000:.2f}ms)"
        )

    return response


# Include Core Operational Routers
app.include_router(auth_router)
app.include_router(overview_router)
app.include_router(incidents_router)
app.include_router(actions_router)
app.include_router(detection_router)
app.include_router(response_policy_router)
app.include_router(federation_router)
app.include_router(governance_router)
app.include_router(pilot_router)

# Include Development Routers only when explicitly allowed
if settings.allow_demo_endpoints:
    app.include_router(dev_router)
    app.include_router(federation_dev_router)
    app.include_router(pilot_dev_router)


@app.get("/healthz", tags=["System"])
def healthz() -> dict[str, Any]:
    """Platform liveness, environment, and response mode status check."""
    return {
        "status": "ok",
        "version": settings.version,
        "environment": settings.environment,
        "mode": settings.response_mode,
        "auto_response_enabled": settings.auto_response_enabled,
        "zero_cost_enforced": settings.enforce_zero_cost,
    }


@app.get("/metrics", tags=["System"])
def prometheus_metrics() -> Response:
    """Prometheus-compatible plain text metrics endpoint."""
    with get_db() as conn:
        tenant_count = conn.execute("SELECT COUNT(*) FROM tenants").fetchone()[0]
        incident_count = conn.execute("SELECT COUNT(*) FROM incidents WHERE status = 'NEW'").fetchone()[0]
        action_count = conn.execute("SELECT COUNT(*) FROM action_journal").fetchone()[0]

    lines = [
        "# HELP fcs_platform_info FCS Platform metadata",
        "# TYPE fcs_platform_info gauge",
        f'fcs_platform_info{{version="{settings.version}",environment="{settings.environment}",mode="{settings.response_mode}"}} 1',
        "# HELP fcs_active_tenants Number of registered active ISP tenants",
        "# TYPE fcs_active_tenants gauge",
        f"fcs_active_tenants {tenant_count}",
        "# HELP fcs_active_incidents Number of unresolved security incidents",
        "# TYPE fcs_active_incidents gauge",
        f"fcs_active_incidents {incident_count}",
        "# HELP fcs_defensive_actions_total Total recorded firewall and mitigation actions",
        "# TYPE fcs_defensive_actions_total counter",
        f"fcs_defensive_actions_total {action_count}",
        "# HELP fcs_zero_cost_enforced Boolean indicating strict ₹0 budget guardrail",
        "# TYPE fcs_zero_cost_enforced gauge",
        f"fcs_zero_cost_enforced {1 if settings.enforce_zero_cost else 0}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@app.get("/", tags=["System"])
def root(request: Request) -> Any:
    """Root info endpoint or frontend entrypoint."""
    accept = request.headers.get("accept", "")
    if ("text/html" in accept or "*/*" in accept) and dist_path.exists() and (dist_path / "index.html").exists():
        return FileResponse(dist_path / "index.html")
    return {
        "service": "Federated Cyber Shield API",
        "version": settings.version,
        "environment": settings.environment,
        "response_mode": settings.response_mode,
        "docs_url": "/docs" if settings.is_development else None,
        "cost_policy": "Strictly ₹0 / $0",
    }


# Mount frontend static distribution directory if built
dist_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "apps" / "security-dashboard" / "dist"
if dist_path.exists():
    app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="frontend")
