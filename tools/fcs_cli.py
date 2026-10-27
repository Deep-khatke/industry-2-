#!/usr/bin/env python3
"""Federated Cyber Shield (FCS) Unified CLI Tool."""

import argparse
import subprocess
import sys
from pathlib import Path

# Add project root and service directories to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
API_SRC = ROOT_DIR / "services" / "api" / "src"
ML_SRC = ROOT_DIR / "services" / "ml_training" / "src"
DATASET_SRC = ROOT_DIR / "services" / "dataset_pipeline" / "src"

for p in [str(ROOT_DIR), str(API_SRC), str(ML_SRC), str(DATASET_SRC)]:
    if p not in sys.path:
        sys.path.insert(0, p)


def cmd_api_start(args: argparse.Namespace) -> int:
    """Start the FastAPI backend server."""
    import uvicorn
    host = args.host or "127.0.0.1"
    port = args.port or 8000
    print(f"[*] Starting FCS API Server at http://{host}:{port} ...")
    uvicorn.run("fcs_api.app:app", host=host, port=port, reload=args.reload)
    return 0


def cmd_demo_seed(args: argparse.Namespace) -> int:
    """Initialize and seed demo database."""
    from fcs_api.database import init_db, seed_demo_data
    print("[*] Initializing FCS Phase 4 SQLite database...")
    init_db()
    print("[*] Seeding 7 ISP tenants, exporters, and demonstration accounts...")
    seed_demo_data()
    print("[+] Database initialized and seeded successfully.")
    return 0


def cmd_demo_reset(args: argparse.Namespace) -> int:
    """Wipe and re-seed demo database."""
    from fcs_api.database import reset_db, seed_demo_data
    print("[*] Resetting demo database...")
    reset_db()
    seed_demo_data()
    print("[+] Demo database reset to pristine baseline.")
    return 0


def cmd_demo_replay(args: argparse.Namespace) -> int:
    """Run reproducible flow replay scenario."""
    from fcs_api.database import init_db, seed_demo_data
    from fcs_api.telemetry.replay import ReplayCoordinator

    init_db()
    seed_demo_data()
    scenario = args.scenario or "suspicious"
    tenant = args.tenant or "rural-isp-alpha"
    print(f"[*] Executing scenario '{scenario}' for tenant '{tenant}'...")
    res = ReplayCoordinator.run_scenario(scenario=scenario, tenant_id=tenant)
    print(f"[+] Replay completed: {res}")
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    """Run automated tests."""
    category = args.category
    test_map = {
        "backend": ["tests/phase4-unit", "tests/phase4-integration"],
        "frontend": ["apps/security-dashboard"],
        "integration": ["tests/phase4-integration"],
        "security": ["tests/phase4-security"],
        "e2e": ["tests/phase4-integration"],
        "regression": ["tests/unit", "tests/ml-unit", "tests/ml-integration"],
        "all": ["tests/"],
    }
    targets = test_map.get(category, ["tests/"])
    if category == "frontend":
        cwd = ROOT_DIR / "apps" / "security-dashboard"
        return subprocess.run(["npm", "test"], cwd=str(cwd), shell=True).returncode

    cmd = [sys.executable, "-m", "pytest"] + targets + ["-v"]
    return subprocess.run(cmd, cwd=str(ROOT_DIR)).returncode


def cmd_verify_phase4(args: argparse.Namespace) -> int:
    """Execute complete Phase 4 release verification script."""
    verify_script = ROOT_DIR / "scripts" / "verify_phase4.py"
    if not verify_script.exists():
        print(f"[-] Verification script not found at {verify_script}")
        return 1
    return subprocess.run([sys.executable, str(verify_script)], cwd=str(ROOT_DIR)).returncode


def main() -> int:
    # If invoked with Phase 8 commands (verify, system, phase8, or test with orchestrator targets), delegate to orchestrator
    if len(sys.argv) > 1 and sys.argv[1] in ("verify", "system", "phase8"):
        from tools.phase8.orchestrator.cli import main as orch_main
        return orch_main(sys.argv[1:])
    if len(sys.argv) > 1 and sys.argv[1] == "test" and len(sys.argv) > 2 and sys.argv[2] in (
        "integration", "adversarial", "resilience", "recovery", "performance", "regression", "end-to-end"
    ):
        from tools.phase8.orchestrator.cli import main as orch_main
        return orch_main(sys.argv[1:])

    parser = argparse.ArgumentParser(prog="fcs", description="Federated Cyber Shield (FCS) Unified CLI")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # api
    p_api = subparsers.add_parser("api", help="Manage API server")
    p_api_sub = p_api.add_subparsers(dest="subaction")
    p_api_start = p_api_sub.add_parser("start", help="Start API dev server")
    p_api_start.add_argument("--host", default="127.0.0.1", help="Host address")
    p_api_start.add_argument("--port", type=int, default=8000, help="Port number")
    p_api_start.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # demo
    p_demo = subparsers.add_parser("demo", help="Manage demo environment and replay")
    p_demo_sub = p_demo.add_subparsers(dest="subaction")
    p_demo_sub.add_parser("seed", help="Seed demo database")
    p_demo_sub.add_parser("reset", help="Reset demo database")
    p_demo_replay = p_demo_sub.add_parser("replay", help="Run traffic replay")
    p_demo_replay.add_argument("--scenario", default="suspicious", choices=["normal", "suspicious", "scanning", "mixed"])
    p_demo_replay.add_argument("--tenant", default="rural-isp-alpha", help="Tenant ID")

    # test
    p_test = subparsers.add_parser("test", help="Execute test suites")
    p_test.add_argument("category", choices=["backend", "frontend", "integration", "security", "e2e", "regression", "all"], default="all", nargs="?")

    # verify-phase4
    subparsers.add_parser("verify-phase4", help="Run Phase 4 release gates and verification")

    # verify
    p_verify = subparsers.add_parser("verify", help="Verification subcommands")
    p_verify.add_argument("target", choices=["prerequisites", "contracts", "security", "privacy", "governance", "models", "response"])

    # system
    p_system = subparsers.add_parser("system", help="System management subcommands")
    p_system.add_argument("target", choices=["start", "status", "health", "stop"])

    # phase8
    p_phase8 = subparsers.add_parser("phase8", help="Phase 8 lifecycle and verification")
    p_phase8.add_argument("target", choices=["run-smoke", "run-full", "report", "verify-release"])

    args = parser.parse_args()

    if args.command in ("verify", "system", "phase8"):
        from tools.phase8.orchestrator.cli import main as orch_main
        return orch_main(sys.argv[1:])
    elif args.command == "api" and args.subaction == "start":
        return cmd_api_start(args)
    elif args.command == "demo" and args.subaction == "seed":
        return cmd_demo_seed(args)
    elif args.command == "demo" and args.subaction == "reset":
        return cmd_demo_reset(args)
    elif args.command == "demo" and args.subaction == "replay":
        return cmd_demo_replay(args)
    elif args.command == "test":
        return cmd_test(args)
    elif args.command == "verify-phase4":
        return cmd_verify_phase4(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
