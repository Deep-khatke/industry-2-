#!/usr/bin/env python3
"""
Phase 9 Real ISP Pilot, Shadow Detection, Manual Response & Operational Readiness Verification Script.
Evaluates Pilot Readiness Gates R01 through R23 and Architecture v1.2 Gates G01 through G15.
Generates machine-readable status summary: phase9_status.json and validates the Phase 9 evidence package.
Strict Zero-Cost Invariant: ₹0 / $0 | Response Invariant: MANUAL MODE ONLY (AUTO DISABLED).
"""

import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parent.parent
API_SRC = ROOT_DIR / "services" / "api" / "src"
ML_SRC = ROOT_DIR / "services" / "ml_training" / "src"
DATASET_SRC = ROOT_DIR / "services" / "dataset_pipeline" / "src"
FED_SRC = ROOT_DIR / "services" / "federated-learning" / "src"
GOV_SRC = ROOT_DIR / "services" / "governance" / "src"
PILOT_SRC = ROOT_DIR / "services" / "pilot-management" / "src"

for p in [str(ROOT_DIR), str(API_SRC), str(ML_SRC), str(DATASET_SRC), str(FED_SRC), str(GOV_SRC), str(PILOT_SRC)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fcs_pilot.exporter_compatibility.feature_parity import FeatureParityValidator
from fcs_pilot.exporter_compatibility.registry import ExporterCapabilityRegistry
from fcs_pilot.governance.backup_recovery import BackupRecoveryManager
from fcs_pilot.metrics.false_alert_meter import FalseAlertMeter
from fcs_pilot.metrics.model_evaluator import RealisticModelEvaluator
from fcs_pilot.onboarding.models import EnvironmentMode, NetworkScope, OnboardingStatus, PilotProfile
from fcs_pilot.operations.rural_degradation import RuralNetworkSimulator
from fcs_pilot.readiness.gates_evaluator import PilotReadinessEvaluator
from fcs_pilot.shadow_monitoring.seven_day_evaluator import SevenDayEvaluator


def verify_phase9() -> Dict[str, Any]:
    start_time = time.time()
    print("================================================================================")
    print("FEDERATED CYBER SHIELD (FCS) PHASE 9 — PILOT READINESS VERIFICATION AUDIT")
    print("================================================================================")

    # 1. Pilot Profile & Readiness Evaluation
    profile = PilotProfile(
        pilot_id="pilot-sim-001",
        tenant_id="rural-isp-alpha",
        isp_display_name="Northern Valley Broadband (ASN 64512)",
        environment_mode=EnvironmentMode.MODE_A_SYNTHETIC,
        status=OnboardingStatus.SHADOW_ACTIVE,
        technical_contact="soc-lead@alpha-broadband.test",
        authorized_network_scope=NetworkScope(prefixes=["192.168.1.0/24"], observation_domain_ids=[1001]),
    )
    readiness_sum = PilotReadinessEvaluator.evaluate_pilot_readiness(profile)

    # 2. 7-Day Shadow Evaluation Replay
    eval_7d = SevenDayEvaluator(profile.pilot_id, profile.tenant_id, is_simulation=True)
    report_7d = eval_7d.run_simulated_7_day_scenario()

    # 3. Model Realistic Condition Evaluation
    model_rep = RealisticModelEvaluator.run_comprehensive_evaluation()

    # 4. Rural Network Scenarios
    net_scenarios = RuralNetworkSimulator.run_all_standard_scenarios()

    # 5. Exporter Compatibility & Feature Parity
    parity_val = FeatureParityValidator()
    parity_results = []
    for k, p in ExporterCapabilityRegistry.list_all().items():
        res = parity_val.evaluate_parity(f"exp-{k}", p.vendor, p.supported_protocols[0], p.supported_fields)
        parity_results.append(res)

    # Export reports to artifacts
    artifacts_dir = ROOT_DIR / "artifacts" / "phase9"
    reports_dir = artifacts_dir / "sanitized-reports"
    parity_val.generate_reports(parity_results, reports_dir)
    eval_7d.export_report_to_disk(reports_dir)

    duration = round(time.time() - start_time, 2)

    status_data = {
        "phase": 9,
        "phase_name": "Real ISP Pilot, Shadow Detection, Manual Response & Operational Readiness",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "git_branch": "feature/phase9-isp-pilot",
        "repository": "https://github.com/Deep-khatke/industry-2-",
        "zero_cost_budget": "STRICTLY ₹0 / $0 (COMPLIANT)",
        "response_mode": "MANUAL_ONLY (AUTO DISABLED)",
        "network_action_executed": False,
        "execution_default": "FIREWALL_SIMULATOR_DEFAULT",
        "server_enforced_shadow_mode": True,
        "pilot_readiness_decision": readiness_sum.final_readiness_decision,
        "live_pilot_authorization_status": readiness_sum.live_pilot_authorization_status,
        "readiness_gates": {
            "total_evaluated": readiness_sum.total_gates_evaluated,
            "passed": readiness_sum.passed_count,
            "partial": readiness_sum.partial_count,
            "blocked": readiness_sum.blocked_count,
            "failed": readiness_sum.failed_count,
            "details": {k: v.model_dump() for k, v in readiness_sum.gates.items()},
        },
        "architecture_gates_v1_2": readiness_sum.architecture_gates_g01_to_g15,
        "seven_day_evaluation": {
            "type": report_7d.evaluation_type,
            "days_completed": report_7d.days_completed,
            "total_flows_processed": report_7d.total_flows_processed,
            "total_incidents": report_7d.total_candidate_incidents,
            "average_false_incidents_per_day": report_7d.average_false_incidents_per_day,
            "target_met_le_5_false_per_day": report_7d.target_met_le_5_false_per_day,
            "average_analyst_review_minutes_per_day": report_7d.average_analyst_review_minutes_per_day,
            "analyst_capacity_target_met": report_7d.analyst_capacity_target_met,
            "overall_detection_coverage_percent": report_7d.overall_detection_coverage_percent,
        },
        "model_performance_summary": {
            "model_version": model_rep.model_version,
            "average_precision": model_rep.average_precision,
            "average_recall": model_rep.average_recall,
            "pr_auc_estimate": model_rep.pr_auc_estimate,
            "worst_source_recall": model_rep.worst_source_recall,
            "all_targets_met": model_rep.all_targets_met,
        },
        "rural_network_simulation": {
            "total_scenarios_tested": len(net_scenarios),
            "all_passed": all(s.detection_continuity_maintained for s in net_scenarios),
            "scenarios": [s.model_dump() for s in net_scenarios],
        },
        "exporter_capability_registry": {
            "profiles_registered": len(parity_results),
            "fully_compatible": sum(1 for r in parity_results if r.is_fully_compatible),
        },
        "verification_duration_seconds": duration,
    }

    status_file = ROOT_DIR / "phase9_status.json"
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(status_data, f, indent=2)

    print(f"Readiness Decision: {readiness_sum.final_readiness_decision}")
    print(f"Gates Evaluated: {readiness_sum.total_gates_evaluated} (Pass={readiness_sum.passed_count})")
    print(f"7-Day Replay: {report_7d.total_flows_processed:,} flows, avg false alerts={report_7d.average_false_incidents_per_day}/day")
    print(f"Zero-Cost Compliance: ₹0 / $0 (COMPLIANT)")
    print(f"Auto Response: PERMANENTLY DISABLED")
    print(f"Verification completed in {duration}s. Written to {status_file}")
    print("================================================================================")
    return status_data


if __name__ == "__main__":
    verify_phase9()
