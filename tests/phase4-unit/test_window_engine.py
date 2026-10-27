"""Unit tests for Phase 4 Event-Time Feature Window Engine."""

from datetime import UTC, datetime, timedelta

from fcs_api.windows.engine import FeatureWindowEngine


def test_window_assignment_and_aggregation():
    engine = FeatureWindowEngine(window_duration_seconds=30, allowed_lateness_seconds=60)
    now_dt = datetime.now(UTC)
    now_str = now_dt.isoformat()

    flow1 = {
        "event_id": "fl_001",
        "tenant_id": "rural-isp-alpha",
        "src_ip": "192.168.1.10",
        "dst_ip": "1.1.1.1",
        "src_port": 40001,
        "dst_port": 443,
        "protocol": "TCP",
        "byte_count": 1500,
        "packet_count": 10,
        "flow_duration_ms": 250.0,
        "tcp_flags": 24,
        "event_time": now_str,
    }

    win1 = engine.process_flow_event(flow1)
    assert win1 is not None
    assert win1["flow_count"] == 1
    assert win1["tenant_id"] == "rural-isp-alpha"
    assert "feature_vector" in win1
    feat = win1["feature_vector"]
    assert feat["IN_BYTES"] == 1500
    assert feat["IN_PKTS"] == 10
    assert feat["L4_DST_PORT"] == 443

    # Add second flow in same window
    flow2 = {
        "event_id": "fl_002",
        "tenant_id": "rural-isp-alpha",
        "src_ip": "192.168.1.11",
        "dst_ip": "1.1.1.1",
        "src_port": 40002,
        "dst_port": 443,
        "protocol": "TCP",
        "byte_count": 2500,
        "packet_count": 15,
        "flow_duration_ms": 300.0,
        "tcp_flags": 24,
        "event_time": now_str,
    }

    win2 = engine.process_flow_event(flow2)
    assert win2 is not None
    assert win2["flow_count"] == 2
    assert win2["feature_vector"]["IN_BYTES"] == 4000
    assert win2["feature_vector"]["IN_PKTS"] == 25


def test_late_event_rejection():
    engine = FeatureWindowEngine(window_duration_seconds=30, allowed_lateness_seconds=60)
    very_old_time = (datetime.now(UTC) - timedelta(minutes=15)).isoformat()

    late_flow = {
        "event_id": "fl_late",
        "tenant_id": "rural-isp-alpha",
        "src_ip": "10.0.0.5",
        "dst_ip": "8.8.8.8",
        "src_port": 5000,
        "dst_port": 53,
        "protocol": "UDP",
        "byte_count": 64,
        "packet_count": 1,
        "flow_duration_ms": 10.0,
        "tcp_flags": 0,
        "event_time": very_old_time,
    }

    win = engine.process_flow_event(late_flow)
    assert win is None, "Events older than allowed_lateness_seconds must be rejected/dropped"
