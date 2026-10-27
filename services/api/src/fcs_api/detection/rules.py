"""Deterministic threat detection rules and heuristics."""

from typing import Any


class ThreatDetectionRules:
    """Evaluates flow attributes and window aggregates against documented detection rules."""

    @staticmethod
    def evaluate(window_data: dict[str, Any], flow_event: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Evaluate detection rules. Returns list of matched rule dictionaries.
        """
        matches: list[dict[str, Any]] = []
        features = window_data.get("feature_vector", {})
        flow_count = window_data.get("flow_count", 1)

        # Rule FCS-R101: High-Volume Flood / DDoS Burst
        in_bytes = features.get("IN_BYTES", 0)
        in_pkts = features.get("IN_PKTS", 0)
        if in_bytes > 500_000 or in_pkts > 2_500 or flow_count > 80:
            matches.append({
                "rule_id": "FCS-R101",
                "rule_name": "Volumetric Flood / DDoS Burst",
                "attack_category": "DDoS",
                "severity": "CRITICAL" if in_bytes > 1_000_000 else "HIGH",
                "description": f"Abnormal traffic volume detected: {in_bytes:,} bytes, {in_pkts:,} packets across {flow_count} flows.",
            })

        # Rule FCS-R102: Port Scanning & Reconnaissance
        dst_port = features.get("L4_DST_PORT", 0)
        tcp_flags = features.get("TCP_FLAGS", 0)
        # TCP SYN flag = 2
        if (tcp_flags == 2 or (flow_event and flow_event.get("tcp_flags") == 2)) and in_pkts < 10:
            matches.append({
                "rule_id": "FCS-R102",
                "rule_name": "SYN Port Scanning / Reconnaissance",
                "attack_category": "PortScan",
                "severity": "MEDIUM",
                "description": f"Repeated TCP SYN probe observed targeting port {dst_port} with low packet completion.",
            })

        # Rule FCS-R103: Abnormal Long-Duration Flow / Slowloris Keepalive
        flow_dur = features.get("FLOW_DURATION_MILLISECONDS", 0.0)
        if flow_dur > 60_000.0 and in_bytes < 5_000:
            matches.append({
                "rule_id": "FCS-R103",
                "rule_name": "Abnormal Flow Duration / Slowloris Keepalive",
                "attack_category": "DoS",
                "severity": "LOW",
                "description": f"Extended TCP connection duration ({flow_dur/1000:.1f}s) with minimal byte exchange.",
            })

        # Rule FCS-R104: Known Malicious Port Targeting (e.g. Mirai 23/2323 Telnet, MS-RDP 3389)
        if dst_port in (23, 2323, 445, 3389, 5060):
            matches.append({
                "rule_id": "FCS-R104",
                "rule_name": "High-Risk Service Probe",
                "attack_category": "Reconnaissance",
                "severity": "MEDIUM",
                "description": f"Probing detected against high-risk service port {dst_port}.",
            })

        return matches
