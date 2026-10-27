"""Performance and Capacity Benchmarking Test Suite for Phase 8 (Profiles P0–P4)."""

import pytest
from tools.phase8.metrics_collector.collector import PerformanceMetricsCollector


def test_performance_nominal_planning_p2():
    """Verify Profile P2 Nominal Planning Load meets throughput and latency SLA targets."""
    collector = PerformanceMetricsCollector()
    res = collector.benchmark_nominal_load(flows_per_sec=1400, duration_seconds=0.5)
    assert res.throughput_flows_per_sec > 1000.0, f"Throughput too low: {res.throughput_flows_per_sec}"
    assert res.latency_p95_ms < 5000.0, f"p95 latency breached: {res.latency_p95_ms}ms"
    assert res.latency_p99_ms < 15000.0, f"p99 latency breached: {res.latency_p99_ms}ms"
    assert res.target_met is True
    assert res.sla_status == "MET"


def test_all_five_performance_profiles():
    """Verify all 5 graduated performance profiles (P0–P4) execute and satisfy resource bounds."""
    collector = PerformanceMetricsCollector()
    summary = collector.run_all_profiles()
    assert summary["all_targets_met"] is True
    profiles = summary["profiles"]
    assert "P0_SMOKE" in profiles
    assert "P1_DEVELOPER" in profiles
    assert "P2_NOMINAL_PLANNING" in profiles
    assert "P3_BURST" in profiles
    assert "P4_FAILURE_RECOVERY" in profiles

    for pid, pdata in profiles.items():
        assert pdata["throughput_flows_sec"] > 0
        assert pdata["latency_p95_ms"] < 5000.0, f"{pid} breached p95 SLA"
        assert pdata["memory_peak_mb"] < 2048.0, f"{pid} exceeded 2GB memory limit"
