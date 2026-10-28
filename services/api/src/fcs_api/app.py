"""FastAPI Application Entry Point for Federated Cyber Shield Phase 4."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
import sys

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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db, seed_demo_data
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
    """Startup and shutdown lifecycle handler."""
    logger.info("Initializing Federated Cyber Shield Phase 4 database and demo data...")
    init_db()
    seed_demo_data()
    logger.info("FCS Backend API initialized successfully.")
    yield
    logger.info("FCS Backend API shutting down.")


app = FastAPI(
    title="Federated Cyber Shield (FCS) API",
    version="1.2.0",
    description="Real-time threat detection, security dashboard backend, and manual response policy engine.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router)
app.include_router(overview_router)
app.include_router(incidents_router)
app.include_router(actions_router)
app.include_router(detection_router)
app.include_router(response_policy_router)
app.include_router(dev_router)
app.include_router(federation_router)
app.include_router(federation_dev_router)
app.include_router(governance_router)
app.include_router(pilot_router)
app.include_router(pilot_dev_router)


@app.get("/healthz", tags=["System"])
def healthz() -> dict[str, str]:
    """Basic platform liveness health check."""
    return {"status": "ok", "version": "1.2.0", "mode": settings.response_mode}


@app.get("/", tags=["System"])
def root() -> dict[str, str]:
    """Root info endpoint."""
    return {
        "service": "Federated Cyber Shield API",
        "version": "1.2.0",
        "response_mode": settings.response_mode,
        "docs_url": "/docs",
        "cost_policy": "Strictly ₹0 / $0",
    }


# Mount frontend static distribution directory if built
dist_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "apps" / "security-dashboard" / "dist"
if dist_path.exists():
    app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="frontend")
