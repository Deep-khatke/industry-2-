"""Command Line Interface for FCS Phase 9 Pilot Management."""

import argparse
import json
import sys
from pathlib import Path

from .exporter_compatibility.checker import ExporterCompatibilityChecker
from .exporter_compatibility.feature_parity import FeatureParityValidator
from .exporter_compatibility.registry import ExporterCapabilityRegistry
from .metrics.false_alert_meter import FalseAlertMeter
from .metrics.model_evaluator import RealisticModelEvaluator
from .onboarding.models import EnvironmentMode, NetworkScope, OnboardingStatus, PilotProfile
from .onboarding.state_machine import OnboardingStateMachine
from .operations.rural_degradation import RuralNetworkSimulator
from .readiness.gates_evaluator import PilotReadinessEvaluator
from .shadow_monitoring.engine import ShadowMonitoringEngine
from .shadow_monitoring.seven_day_evaluator import SevenDayEvaluator


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="fcs-pilot",
        description="Federated Cyber Shield (FCS) Phase 9 ISP Pilot & Shadow Operations CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = subparsers.add_parser("status", help="Display Phase 9 operational status and invariants")

    # onboard
    p_onboard = subparsers.add_parser("onboard", help="List and inspect ISP pilot onboarding profiles")

    # exporters
    p_exp = subparsers.add_parser("exporters", help="List exporter registry profiles and test compatibility")

    # parity
    p_parity = subparsers.add_parser("parity", help="Verify FeatureSpec v1.2 parity across router exporters")

    # shadow
    p_shadow = subparsers.add_parser("shadow", help="Run server-enforced shadow detection demonstration")

    # seven-day
    p_seven = subparsers.add_parser("seven-day", help="Run 7-day shadow evaluation scenario")

    # readiness
    p_ready = subparsers.add_parser("readiness", help="Evaluate all 23 readiness gates and produce verdict")

    args = parser.parse_args()

    if args.command == "status":
        print("=" * 60)
        print("FEDERATED CYBER SHIELD — PHASE 9 ISP PILOT OPERATIONS")
        print("=" * 60)
        print("Version: 1.2.0")
        print("Budget: STRICTLY ₹0 / $0 (COMPLIANT)")
        print("Response Mode: MANUAL_ONLY (AUTO DISABLED)")
        print("Network Action Executed: False")
        print("Execution Default: FIREWALL_SIMULATOR_DEFAULT")
        print("Architecture Gates: G01-G12, G14-G15 [PASS], G13 [BLOCKED / NOT_ENABLED]")
        print("=" * 60)
        return 0

    elif args.command == "onboard":
        profiles = [
            PilotProfile(
                pilot_id="pilot-sim-001",
                tenant_id="rural-isp-alpha",
                isp_display_name="Northern Valley Broadband (ASN 64512)",
                environment_mode=EnvironmentMode.MODE_A_SYNTHETIC,
                status=OnboardingStatus.SHADOW_ACTIVE,
                technical_contact="soc-lead@alpha-broadband.test",
                authorized_network_scope=NetworkScope(prefixes=["192.168.1.0/24"], observation_domain_ids=[1001]),
            ),
            PilotProfile(
                pilot_id="pilot-real-template-001",
                tenant_id="prospective-real-isp",
                isp_display_name="Prospective Production ISP Partner",
                environment_mode=EnvironmentMode.MODE_B_REAL_SHADOW,
                status=OnboardingStatus.PILOT_BLOCKED,
                technical_contact="partner-noc@prospective-isp.example",
                blocker_reason="LIVE_PILOT_BLOCKED: Formal written authorization pending.",
            ),
        ]
        sm = OnboardingStateMachine(profiles)
        print("ISP Pilot Profiles:")
        for p in sm.list_profiles():
            print(f" - [{p.status}] {p.pilot_id}: {p.isp_display_name} (Mode: {p.environment_mode})")
            if p.blocker_reason:
                print(f"   Blocker: {p.blocker_reason}")
        return 0

    elif args.command == "exporters":
        profiles = ExporterCapabilityRegistry.list_all()
        print(f"Registered Exporter Families ({len(profiles)}):")
        for k, p in profiles.items():
            print(f" - {p.vendor} {p.device_family} ({'/'.join(p.supported_protocols)}): {len(p.supported_fields)} fields")
        return 0

    elif args.command == "parity":
        val = FeatureParityValidator()
        res = val.evaluate_parity(
            exporter_id="exp-alpha-cisco-01",
            vendor="Cisco",
            protocol="IPFIX",
            available_fields=[
                "sourceIPv4Address", "destinationIPv4Address", "sourceTransportPort",
                "destinationTransportPort", "protocolIdentifier", "octetDeltaCount",
                "packetDeltaCount", "tcpControlBits", "flowStartMilliseconds", "flowEndMilliseconds",
            ],
        )
        print(f"Feature Parity for {res.exporter_id} ({res.vendor}): {res.parity_percentage}%")
        print(f"Matched ({len(res.matched_features)}): {', '.join(res.matched_features)}")
        print(f"Eligible Specialists: {', '.join(res.compatible_models)}")
        return 0

    elif args.command == "shadow":
        engine = ShadowMonitoringEngine("rural-isp-alpha", shadow_mode_enabled=True)
        # Test synthetic telemetry window
        cand = engine.process_telemetry_window(
            exporter_id="exp-alpha-core-01",
            window_features={
                "src_ip": "198.51.100.44",
                "dst_ip": "192.168.1.100",
                "protocol": 6,
                "tcp_flags": 2,  # SYN
                "packet_count": 8500,
                "byte_count": 340000,
            },
        )
        print("Shadow Monitoring Engine Execution:")
        print(f" - Flows Ingested: {engine.get_metrics()['total_flows_ingested']}")
        print(f" - Network Action Executed: {engine.get_metrics()['network_action_executed']}")
        if cand:
            print(f" - Candidate Incident Generated: {cand.candidate_id} ({cand.attack_class})")
            print(f" - Recommendation Status: {cand.advisory_recommendation['execution_status']}")
        return 0

    elif args.command == "seven-day":
        evaluator = SevenDayEvaluator("pilot-sim-001", "rural-isp-alpha", is_simulation=True)
        report = evaluator.run_simulated_7_day_scenario()
        print(f"7-Day Shadow Evaluation ({report.evaluation_type}):")
        print(f" - Days Completed: {report.days_completed}")
        print(f" - Total Flows Processed: {report.total_flows_processed:,}")
        print(f" - Total Incidents: {report.total_candidate_incidents}")
        print(f" - Average False Alerts/Day: {report.average_false_incidents_per_day} (Target <= 5.0: {report.target_met_le_5_false_per_day})")
        print(f" - Average Analyst Time: {report.average_analyst_review_minutes_per_day} mins/day (Budget <= 20.0: {report.analyst_capacity_target_met})")
        print(f" - Verdict: {report.recommendation}")
        return 0

    elif args.command == "readiness":
        profile = PilotProfile(
            pilot_id="pilot-sim-001",
            tenant_id="rural-isp-alpha",
            isp_display_name="Northern Valley Broadband",
            environment_mode=EnvironmentMode.MODE_A_SYNTHETIC,
            status=OnboardingStatus.SHADOW_ACTIVE,
            technical_contact="soc-lead@alpha-broadband.test",
        )
        summary = PilotReadinessEvaluator.evaluate_pilot_readiness(profile)
        print(f"Pilot Readiness Assessment ({summary.pilot_id}):")
        print(f" - Gates Evaluated: {summary.total_gates_evaluated}")
        print(f" - Passed: {summary.passed_count}, Partial: {summary.partial_count}, Blocked: {summary.blocked_count}")
        print(f" - Final Readiness Decision: {summary.final_readiness_decision}")
        print(f" - Live Pilot Authorization: {summary.live_pilot_authorization_status}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
