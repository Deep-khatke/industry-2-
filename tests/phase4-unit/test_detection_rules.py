"""Unit tests for deterministic threat detection rules."""

from fcs_api.detection.rules import ThreatDetectionRules


def test_rule_fcs_r101_volumetric_flood():
    # Volumetric burst triggering R101
    window_data = {
        "tenant_id": "rural-isp-alpha",
        "flow_count": 100,
        "feature_vector": {
            "IN_BYTES": 1_200_000,
            "IN_PKTS": 4_000,
            "L4_DST_PORT": 80,
            "TCP_FLAGS": 16,
            "FLOW_DURATION_MILLISECONDS": 500.0,
        },
    }
    matches = ThreatDetectionRules.evaluate(window_data)
    rule_ids = [m["rule_id"] for m in matches]
    assert "FCS-R101" in rule_ids
    r101 = next(m for m in matches if m["rule_id"] == "FCS-R101")
    assert r101["attack_category"] == "DDoS"
    assert r101["severity"] == "CRITICAL"


def test_rule_fcs_r102_syn_scan():
    # SYN probe triggering R102
    window_data = {
        "tenant_id": "rural-isp-alpha",
        "flow_count": 1,
        "feature_vector": {
            "IN_BYTES": 44,
            "IN_PKTS": 1,
            "L4_DST_PORT": 22,
            "TCP_FLAGS": 2,  # SYN flag
            "FLOW_DURATION_MILLISECONDS": 20.0,
        },
    }
    flow_event = {"tcp_flags": 2, "dst_port": 22}
    matches = ThreatDetectionRules.evaluate(window_data, flow_event=flow_event)
    rule_ids = [m["rule_id"] for m in matches]
    assert "FCS-R102" in rule_ids
    r102 = next(m for m in matches if m["rule_id"] == "FCS-R102")
    assert r102["attack_category"] == "PortScan"


def test_benign_traffic_no_rules_matched():
    # Benign normal HTTP flow
    window_data = {
        "tenant_id": "rural-isp-alpha",
        "flow_count": 5,
        "feature_vector": {
            "IN_BYTES": 12_000,
            "IN_PKTS": 15,
            "L4_DST_PORT": 443,
            "TCP_FLAGS": 24,  # PSH-ACK
            "FLOW_DURATION_MILLISECONDS": 350.0,
        },
    }
    matches = ThreatDetectionRules.evaluate(window_data)
    assert len(matches) == 0, "Benign HTTP traffic must not match threat detection rules"
