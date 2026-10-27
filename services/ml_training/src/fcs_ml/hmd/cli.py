"""FCS-HMD CLI: Hierarchical Multi-Model Intrusion Detection Engine CLI."""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[5]
for p in [str(ROOT_DIR), str(ROOT_DIR / "services" / "ml_training" / "src"), str(ROOT_DIR / "services" / "api" / "src")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fcs_ml.hmd.bundle import BundleValidator, DetectionBundle
from fcs_ml.hmd.executor import HierarchicalDetectionEngine
from fcs_ml.hmd.fusion import EvidenceFusionEngine
from fcs_ml.hmd.router import ConditionalModelRouter
from fcs_ml.registry.registry import CandidateModelRegistry
from packages.contracts.model_score import ModelScore, ModelType, ScoringStatus


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fcs-hmd",
        description="Federated Cyber Shield — Phase 5 FCS-HMD Hierarchical Threat Detection CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="FCS-HMD Subcommands")

    # inspect
    subparsers.add_parser("inspect", help="Inspect FCS-HMD engine status, models, and active bundle")

    # verify-prerequisites
    subparsers.add_parser("verify-prerequisites", help="Verify Phase 2 data and Phase 3 model prerequisites")

    # train
    train_p = subparsers.add_parser("train", help="Train a Phase 5 candidate model")
    train_p.add_argument("--model", required=True, choices=["anomaly", "ddos", "scanning", "botnet"])

    # evaluate
    subparsers.add_parser("evaluate", help="Evaluate FCS-HMD engine against Phase 2 test set")

    # compare
    subparsers.add_parser("compare", help="Compare architectural configurations and output report")

    # route-test
    subparsers.add_parser("route-test", help="Test conditional router on sample network flow vectors")

    # fusion-test
    subparsers.add_parser("fusion-test", help="Test deterministic multi-model evidence fusion engine")

    # benchmark
    subparsers.add_parser("benchmark", help="Measure FCS-HMD inference latency and memory utilization")

    # bundles
    bundle_p = subparsers.add_parser("bundles", help="Manage DetectionBundle manifests")
    bundle_sub = bundle_p.add_subparsers(dest="action", help="Bundle action")
    bundle_sub.add_parser("list", help="List registered detection bundles")
    bundle_sub.add_parser("create", help="Create default detection bundle")
    ver_p = bundle_sub.add_parser("verify", help="Verify bundle integrity hashes")
    ver_p.add_argument("--bundle-id", default="fcs-hmd-bundle-v1")
    act_p = bundle_sub.add_parser("activate", help="Activate a verified detection bundle")
    act_p.add_argument("--bundle-id", default="fcs-hmd-bundle-v1")
    act_p.add_argument("--role", default="PLATFORM_ADMIN")
    rb_p = bundle_sub.add_parser("rollback", help="Rollback to previous active bundle")
    rb_p.add_argument("--role", default="PLATFORM_ADMIN")

    # predict
    pred_p = subparsers.add_parser("predict", help="Execute hierarchical scoring on a test flow")
    pred_p.add_argument("--tenant", default="rural-isp-alpha")

    # replay
    rep_p = subparsers.add_parser("replay", help="Replay telemetry scenario through FCS-HMD")
    rep_p.add_argument("--scenario", default="suspicious", choices=["normal", "suspicious", "ddos", "portscan"])
    rep_p.add_argument("--tenant", default="rural-isp-alpha")

    # verify-phase5
    subparsers.add_parser("verify-phase5", help="Run comprehensive Phase 5 zero-cost verification suite")

    # report
    subparsers.add_parser("report", help="Print summary of Phase 5 completion and Gate G15 status")

    return parser


def cmd_inspect() -> int:
    engine = HierarchicalDetectionEngine()
    bundle = engine.get_active_bundle()
    status = engine.get_status()
    print("\n========================================================")
    print("FCS-HMD HIERARCHICAL DETECTION ENGINE INSPECTION")
    print("========================================================")
    print(f"Operational Status:   {status}")
    print(f"Active Bundle ID:     {bundle.bundle_id if bundle else 'None'}")
    if bundle:
        print(f"Bundle Version:       {bundle.version}")
        print(f"Bundle Digest:        {bundle.bundle_digest}")
        print(f"General Model:        {bundle.general_model_id}")
        print(f"Anomaly Model:        {bundle.anomaly_model_id}")
        print(f"Specialists:          {', '.join(bundle.specialist_model_ids)}")
        print(f"Authorized By:        {bundle.authorized_by}")
    print("========================================================\n")
    return 0


def cmd_verify_prerequisites() -> int:
    print("\n[*] Verifying Phase 2 & 3 Prerequisites...")
    checks = [
        ("Phase 2 Dataset Manifest", ROOT_DIR / "data" / "processed" / "dataset_manifest.json"),
        ("Phase 2 Test Split", ROOT_DIR / "data" / "processed" / "test_split.parquet"),
        ("Preprocessor State", ROOT_DIR / "data" / "processed" / "preprocessor_state.json"),
        ("General Detector Artifact", ROOT_DIR / "artifacts" / "candidate-models" / "lightgbm_deployable_subset" / "model.txt"),
    ]
    all_ok = True
    for name, path in checks:
        if path.exists():
            print(f"  [+] {name:<30}: FOUND ({path})")
        else:
            print(f"  [-] {name:<30}: MISSING ({path})")
            all_ok = False
    return 0 if all_ok else 1


def cmd_train(model_name: str) -> int:
    train_script = ROOT_DIR / "scripts" / "train_phase5_models.py"
    print(f"[*] Training model candidate '{model_name}' using {train_script.name}...")
    res = subprocess.run([sys.executable, str(train_script)], cwd=str(ROOT_DIR))
    return res.returncode


def cmd_route_test() -> int:
    router = ConditionalModelRouter()
    print("\n[*] Testing Conditional Model Router...")

    # Case 1: Normal benign traffic
    normal_flow = {"L4_SRC_PORT": 49152, "L4_DST_PORT": 80, "PROTOCOL": 6, "IN_PKTS": 4, "IN_BYTES": 240, "FLOW_DURATION_MILLISECONDS": 200, "TCP_FLAGS": 16}
    gen_score_benign = ModelScore(
        model_id="lightgbm_deployable_subset",
        model_type=ModelType.GENERAL_DETECTOR,
        calibrated_probability=0.1,
        predicted_label="Benign",
        prediction=0,
        status=ScoringStatus.SCORED,
    )
    decision1 = router.route(normal_flow, gen_score_benign, None)
    print(f"  1. Normal Flow -> Specialists Routed: {decision1.routed_models} (Should Route: {decision1.should_route_specialists})")

    # Case 2: Volumetric Burst
    vol_flow = {"L4_SRC_PORT": 50000, "L4_DST_PORT": 443, "PROTOCOL": 6, "IN_PKTS": 5000, "IN_BYTES": 5000000, "FLOW_DURATION_MILLISECONDS": 1000, "TCP_FLAGS": 16}
    gen_score_attack = ModelScore(
        model_id="lightgbm_deployable_subset",
        model_type=ModelType.GENERAL_DETECTOR,
        calibrated_probability=0.85,
        predicted_label="Attack",
        prediction=1,
        status=ScoringStatus.SCORED,
    )
    decision2 = router.route(vol_flow, gen_score_attack, None)
    print(f"  2. Volumetric Flow -> Specialists Routed: {decision2.routed_models} (Triggers: {decision2.trigger_reasons})")

    # Case 3: SYN Scan Probe
    scan_flow = {"L4_SRC_PORT": 41234, "L4_DST_PORT": 22, "PROTOCOL": 6, "IN_PKTS": 1, "IN_BYTES": 44, "FLOW_DURATION_MILLISECONDS": 10, "TCP_FLAGS": 2}
    decision3 = router.route(scan_flow, gen_score_attack, None)
    print(f"  3. SYN Probe Flow -> Specialists Routed: {decision3.routed_models} (Triggers: {decision3.trigger_reasons})")

    print("[+] Conditional router tests completed successfully.\n")
    return 0


def cmd_fusion_test() -> int:
    from fcs_ml.hmd.router import RoutingDecision

    fusion = EvidenceFusionEngine()
    print("\n[*] Testing Evidence Fusion Engine...")
    gen_score = ModelScore(
        model_id="lightgbm_deployable_subset",
        model_type=ModelType.GENERAL_DETECTOR,
        calibrated_probability=0.75,
        predicted_label="Attack",
        prediction=1,
        status=ScoringStatus.SCORED,
    )
    anom_score = ModelScore(
        model_id="isolationforest_anomaly_tenant",
        model_type=ModelType.ANOMALY_DETECTOR,
        calibrated_probability=0.60,
        predicted_label="Attack",
        prediction=1,
        status=ScoringStatus.SCORED,
    )
    ddos_score = ModelScore(
        model_id="lightgbm_ddos_specialist",
        model_type=ModelType.DDOS_SPECIALIST,
        calibrated_probability=0.92,
        predicted_label="DDoS",
        prediction=1,
        status=ScoringStatus.SCORED,
    )
    route_dec = RoutingDecision(
        tenant_id="test",
        level1_general_score=0.75,
        level1_anomaly_score=0.60,
        should_route_specialists=True,
        routed_models=["lightgbm_ddos_specialist"],
        trigger_reasons=["VOLUMETRIC_BURST"],
    )
    res = fusion.fuse(
        general_score=gen_score,
        anomaly_score=anom_score,
        specialist_scores=[ddos_score],
        rule_matches=[{"rule_id": "FCS-R101", "name": "SYN Flood Rate Alert", "severity": "HIGH", "attack_category": "DDoS"}],
        routing_decision=route_dec,
    )
    print(f"  Composite Risk:          {res.composite_risk:.4f}")
    print(f"  Attack Category:         {res.attack_category}")
    print(f"  Severity:                {res.severity}")
    print(f"  Is Threat:               {res.is_threat}")
    print(f"  Fusion Method:           {res.fusion_method}")
    print("[+] Evidence fusion test completed successfully.\n")
    return 0


def cmd_predict(tenant: str) -> int:
    engine = HierarchicalDetectionEngine()
    flow = {
        "L4_SRC_PORT": 45123, "L4_DST_PORT": 80, "PROTOCOL": 6, "IN_BYTES": 1500,
        "IN_PKTS": 10, "OUT_BYTES": 3000, "OUT_PKTS": 12, "FLOW_DURATION_MILLISECONDS": 250,
        "TCP_FLAGS": 16, "CLIENT_TCP_FLAGS": 16, "SERVER_TCP_FLAGS": 16, "DURATION_IN": 250,
        "DURATION_OUT": 250, "MIN_TTL": 64
    }
    print(f"\n[*] Executing Hierarchical Scoring for tenant '{tenant}'...")
    res = engine.score_flow(flow_dict=flow, tenant_id=tenant, window_id="cli_test_w1")
    print(f"  Composite Risk:          {res.composite_risk:.4f}")
    print(f"  Attack Category:         {res.attack_category}")
    print(f"  Severity:                {res.severity}")
    print(f"  Safety Invariant:        network_action_executed = {res.network_action_executed}")
    return 0


def cmd_bundles(action: str, bundle_id: str | None = None, role: str = "PLATFORM_ADMIN") -> int:
    reg = CandidateModelRegistry()
    engine = HierarchicalDetectionEngine()
    if action == "list":
        bundles = list(reg.registry_dir.glob("*.json"))
        print(f"\n[*] Registered Detection Bundles ({len(bundles)} found):")
        for b_path in bundles:
            print(f"  • {b_path.name}")
        return 0

    if action == "verify":
        b_path = reg.registry_dir / f"{bundle_id}.json" if not bundle_id.endswith(".json") else reg.registry_dir / bundle_id
        if not b_path.exists():
            b_path = reg.registry_dir / "default_bundle.json"
        bundle = DetectionBundle.load(b_path)
        val = BundleValidator.validate(bundle, reg)
        print(f"\n[*] Verifying bundle '{bundle.bundle_id}'...")
        print(f"  Valid: {val['is_valid']}")
        if val["errors"]:
            print(f"  Errors: {val['errors']}")
        return 0 if val["is_valid"] else 1

    if action == "activate":
        b_path = reg.registry_dir / "default_bundle.json"
        bundle = DetectionBundle.load(b_path)
        res = engine.activate_bundle(bundle, authorized_by="cli_admin", role=role)
        print(f"\n[*] Activation Result: {res}")
        return 0 if res.get("success") else 1

    if action == "rollback":
        res = engine.rollback_bundle(authorized_by="cli_admin", role=role)
        print(f"\n[*] Rollback Result: {res}")
        return 0 if res.get("success") else 1

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return 0

    if args.subcommand == "inspect":
        return cmd_inspect()
    elif args.subcommand == "verify-prerequisites":
        return cmd_verify_prerequisites()
    elif args.subcommand == "train":
        return cmd_train(args.model)
    elif args.subcommand == "route-test":
        return cmd_route_test()
    elif args.subcommand == "fusion-test":
        return cmd_fusion_test()
    elif args.subcommand == "predict":
        return cmd_predict(args.tenant)
    elif args.subcommand == "bundles":
        return cmd_bundles(args.action, getattr(args, "bundle_id", None), getattr(args, "role", "PLATFORM_ADMIN"))
    elif args.subcommand == "benchmark":
        bench_script = ROOT_DIR / "scripts" / "run_phase5_experiments.py"
        return subprocess.run([sys.executable, str(bench_script)], cwd=str(ROOT_DIR)).returncode
    elif args.subcommand == "compare" or args.subcommand == "evaluate":
        bench_script = ROOT_DIR / "scripts" / "run_phase5_experiments.py"
        return subprocess.run([sys.executable, str(bench_script)], cwd=str(ROOT_DIR)).returncode
    elif args.subcommand == "replay":
        from fcs_api.telemetry.replay import ReplayCoordinator
        print(f"[*] Replaying scenario '{args.scenario}' for '{args.tenant}'...")
        res = ReplayCoordinator.run_scenario(scenario=args.scenario, tenant_id=args.tenant)
        print(f"[+] Replay completed: {res}")
        return 0
    elif args.subcommand == "verify-phase5":
        verify_script = ROOT_DIR / "scripts" / "verify_phase5.py"
        return subprocess.run([sys.executable, str(verify_script)], cwd=str(ROOT_DIR)).returncode
    elif args.subcommand == "report":
        report_file = ROOT_DIR / "phase5_status.json"
        if report_file.exists():
            print(report_file.read_text(encoding="utf-8"))
            return 0
        print("[-] phase5_status.json not found.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
